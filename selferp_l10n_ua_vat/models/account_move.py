import json
import re

from textwrap import shorten

from odoo import fields, models, api, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_date, date_utils
from odoo.tools.misc import formatLang

from odoo.addons.selferp_l10n_ua_ext.utils.export_xml import export_xml_extract_doc_number, export_xml_create_base_head, export_xml_file_name, export_xml_format_number, xml_prettify


VAT_INVOICE_STAGES = [
    ('draft', "Draft"),
    ('prepared', "Prepared"),
    ('on_registration', "On registration"),
    ('blocked', "Blocked"),
    ('registered', "Registered"),
    ('cancelled', "Cancelled"),
]

VAT_NON_PAYERS = {
    '01': '100000000000',
    '02': '100000000000',
    '03': '400000000000',
    '04': '600000000000',
    '05': '400000000000',
    '06': '400000000000',
    '07': '300000000000',
    '08': '600000000000',
    '09': '600000000000',
    '10': '600000000000',
    '11': '100000000000',
    '13': '600000000000',
    '14': '500000000000',
    '21': '500000000000',
    '22': '300000000000',
}

VAT_MOVE_TYPES = {
    'vat_invoice',
    'vat_adjustment_invoice',
    'vendor_vat_invoice',
    'vendor_vat_adjustment_invoice',
}


DOC_VAT_INVOICE = 'J1201015'
DOC_VAT_ADJUSTMENT_INVOICE = 'J1201215'

VAT_ACTIONS = [
    'selferp_l10n_ua_vat.account_move_action_vat_adjustment_invoice',
    'selferp_l10n_ua_vat.account_move_action_vat_invoice',
    'selferp_l10n_ua_vat.account_move_action_vendor_vat_invoice',
    'selferp_l10n_ua_vat.account_move_view_tree_vat_invoice',
    'selferp_l10n_ua_vat.account_move_view_tree_vendor_vat_invoice',
]
VAT_ACTIONS_REMOVE_PRINTS = [
    'account.account_invoices',
    'account.account_invoices_without_payment',
    'account.action_account_original_vendor_bill',
    'selferp_l10n_ua_sale_print_form.account_move_report_act',
    'selferp_l10n_ua_sale_print_form.account_move_report_invoice',
]
VAT_ACTIONS_REMOVE_ACTIONS = [
    'account.action_account_invoice_from_list',
    'account.action_move_switch_invoice_to_credit_note',
    'account.action_view_account_move_reversal',
    'account_debit_note.action_view_account_move_debit',
    'account_invoice_extract.model_account_send_for_digitalization',
    'account.invoice_send',
    'account_payment.action_invoice_order_generate_link',
]
VAT_ACTIONS_REMOVE_IN_NON_VAT = [
    'selferp_l10n_ua_vat.account_move_action_vat_export_xml',
    'selferp_l10n_ua_vat.account_move_action_vat_import_xml',
    'selferp_l10n_ua_vat.account_move_vat_invoice_change_stage_action',
]


def format_grn(env, val):
    return formatLang(env, val, monetary=True, currency_obj=env.company.currency_id)


class AccountMove(models.Model):
    _inherit = 'account.move'

    price_change_mode = fields.Boolean(
        string="Price Change",
        default=False,
        states={'posted': [('readonly', True)]},
    )

    move_type = fields.Selection(
        selection_add=[
            ('vat_invoice', "VAT Invoice"),
            ('vat_adjustment_invoice', "VAT Adjustment Invoice"),
            ('vendor_vat_invoice', "Vendor VAT Invoice"),
            ('vendor_vat_adjustment_invoice', "Vendor VAT Adjustment Invoice"),
        ],
        ondelete={
            'vat_invoice': 'set default',
            'vat_adjustment_invoice': 'set default',
            'vendor_vat_invoice': 'set default',
            'vendor_vat_adjustment_invoice': 'set default',
        },
    )
    vat_invoice_stage = fields.Selection(
        selection=VAT_INVOICE_STAGES,
        string="Stage",
        required=True,
        default='draft',
        copy=False,
        tracking=True,
    )
    registration_due_date = fields.Date(
        string="Registration due date",
        compute='_compute_registration_due_date',
        store=True,
        readonly=False,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
        index=True,
        copy=False,
    )
    registration_date = fields.Date(
        string="Registration date",
        states={'posted': [('readonly', True)]},
        copy=False,
    )

    vat_line_ids = fields.One2many(
        comodel_name='account.move.vat.line',
        inverse_name='move_id',
        states={'posted': [('readonly', True)]},
        copy=True,
        string="VAT lines",
    )

    vat_line_total = fields.Monetary(
        string="VAT Total",
        compute='_compute_vat_amount',
        store=True,
    )
    vat_line_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_vat_amount',
        store=True,
    )
    vat_line_tax = fields.Monetary(
        string="VAT Tax",
        compute='_compute_vat_amount',
        store=True,
    )

    vat_line_total_vat_base = fields.Monetary(
        string="VAT base",
        compute='_compute_vat_amount',
        compute_sudo=True,
    )

    vat_line_tax_totals = fields.Binary(
        string="VAT Totals",
        compute='_compute_vat_tax_totals',
    )

    vat = fields.Char(
        compute='_compute_vat',
        store=True,
        readonly=False,
        states={'posted': [('readonly', True)]},
        string="VAT",
    )
    responsible_person_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Responsible",
        states={'posted': [('readonly', True)]},
    )
    customer_branch_number = fields.Char(
        string="Customer Branch Number",
        states={'posted': [('readonly', True)]},
    )
    not_issued_to_customer = fields.Boolean(
        string="Not Issued to the Customer",
        default=False,
        states={'posted': [('readonly', True)]},
    )
    reason_type = fields.Selection(
        selection=[
            ('01', "01 - Composed of the amount of increase in compensation for the cost of delivered goods/services delivered"),
            ('02', "02 - Prepared for delivery to a non-taxpayer"),
            ('03', "03 - Drawn up for the supply of goods/services against remuneration to individuals who are in an employment relationship with the taxpayer"),
            ('04', "04 - Prepared for delivery within the balance sheet for non-production use"),
            ('05', "05 - Prepared in connection with the liquidation of fixed assets by the taxpayer's own decision"),
            ('06', "06 - Composed in connection with the transfer of production fixed assets to non-production fixed assets"),
            ('07', "07 - Imposed on transactions for the export of goods outside the customs territory of Ukraine"),
            ('08', "08 - Compiled for supply for transactions that are not subject to value added tax"),
            ('09', "09 - Accrued for supplies for transactions that are exempt from value added tax"),
            ('10', "10 - Compiled for the purpose of determining, upon cancellation of the taxpayer's registration, tax liabilities for goods/services, non-current assets, the tax amounts for which were included in the tax credit and were not used in taxable transactions within the business activity"),
            ('11', "11 - Compiled on the basis of daily transaction results"),
            ('12', "12 - Drawn up for delivery to a non-payer, indicating the name of the buyer"),
            ('13', "13 - Composed in connection with the use of production or non-production assets, other goods/services not in economic activity"),
            ('14', "14 - Drawn up by the recipient (buyer) of services from a non-resident"),
            ('15', "15 - Composed of the excess of the tax base determined in accordance with Articles 188 and 189 of the Tax Code of Ukraine over the actual delivery price"),
            ('21', "21 - Drawn up for the supply of services to a non-resident recipient (buyer), the place of supply of which is located in the customs territory of Ukraine"),
            ('22', "22 - Drawn up for transactions on the export outside the customs territory of Ukraine of goods subject to the export security regime, which are subject to value added tax at the basic rate or the rate of 14 percent"),
        ],
        states={'posted': [('readonly', True)]},
        string="Reason type",
    )
    consolidated_vat_invoice = fields.Boolean(
        string="Consolidated Tax Invoice",
        default=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    consolidated_tax_code = fields.Selection(
        selection=[
            ('1', "in case of accrual of tax liabilities in accordance with clause 198.5 of the TCU"),
            ('2', "in case of accrual of tax liabilities in accordance with clause 199.1 of the TCU"),
            ('3', "in case of preparation of consolidated tax invoices in accordance with clause 15 of Order 1307"),
            ('4', "in case of preparation of consolidated tax invoices in accordance with clause 19 of Order 1307"),
        ],
        string="Consolidated Tax Code",
        states={'posted': [('readonly', True)]},
        copy=False,
    )

    first_event_vat_invoice_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='cascade',
        string="VAT invoice",
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    vat_cause_type_adjustment = fields.Selection(
        selection=[
            ('quantity', "Quantity Adjustment"),
            ('price', "Price Adjustment"),
        ],
        string="Cause Type Adjustment",
        states={'posted': [('readonly', True)]},
        default='quantity',
        copy=False,
    )
    first_event_source_id = fields.Many2one(
        comodel_name='account.move',
        string="VAT First Event Source",
        states={'posted': [('readonly', True)]},
    )
    vat_fully_reconciled = fields.Boolean(
        string="Is VAT Fully Reconciled",
        compute='_compute_vat_fully_reconciled',
    )
    vat_vendor_reconcilable = fields.Boolean(
        string="Is Vendor VAT Reconcilable",
        compute='_compute_vat_vendor_reconcilable',
    )

    vat_invoice_adjustment_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="VAT Invoice for Adjustment",
        domain="[('partner_id', '=', partner_id), ('move_type', '=', 'vat_invoice')]",
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    registration_type_adjustment = fields.Selection(
        selection=[
            ('by_vendor', "by Vendor"),
            ('by_customer', "by Customer"),
        ],
        string="Registration Type",
        default='by_vendor',
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    to_consolidated_vat_invoice = fields.Boolean(
        string="To the Consolidated VAT Invoice",
        states={'posted': [('readonly', True)]},
        default=False,
    )
    to_vat_invoice_exempt_from_taxation = fields.Boolean(
        string="To the VAT Invoice Exempt from Taxation",
        states={'posted': [('readonly', True)]},
        default=False,
    )
    vat_invoice_no_obligation = fields.Boolean(
        string="Use no obligation VAT account",
        default=False,
        states={'posted': [('readonly', True)]},
    )
    vat_invoice_not_standard_account_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Not standard account for operations with VAT",
    )
    vat_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        ondelete='cascade',
        string="VAT Sale Order",
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    composed_of_tax_exempt_transactions = fields.Boolean(
        string="Composed of Tax-exempt Transactions",
        default=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    external_number = fields.Char(
        string="External number",
        states={'posted': [('readonly', True)]},
    )
    issuance_date = fields.Date(
        string="Issuance Date",
        states={'posted': [('readonly', True)]},
    )
    cash_method = fields.Boolean(
        string="Cash Method",
        default=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    not_used_in_business_operations = fields.Boolean(
        string="Not Used in Business Operations",
        default=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    vendor_vat_invoice_type = fields.Selection(
        selection=[
            ('vendor_vat_invoice', "Vendor VAT Invoice"),
            ('vendor_vat_adjustment_invoice', "Vendor VAT Adjustment Invoice"),
        ],
        string="Document type",
        compute='_compute_vendor_vat_invoice_type',
        inverse='_inverse_vendor_vat_invoice_type',
        states={'posted': [('readonly', True)]},
    )
    vendor_vat_invoice_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="Vendor VAT Invoice",
        domain="[('partner_id', '=', partner_id), ('move_type', '=', 'vendor_vat_invoice')]",
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    acquisition_non_current_assets = fields.Boolean(
        string="Acquisition of non-current Assets",
        default=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )
    vat_contract_ids = fields.Many2many(
        comodel_name='account.contract',
        compute='_compute_vat_relations',
        string="VAT Contracts",
    )
    vat_contract_count = fields.Integer(
        compute='_compute_vat_relations',
        string="VAT Contract Count",
    )
    vat_sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        compute='_compute_vat_relations',
        string="VAT Sale Orders",
    )
    vat_sale_order_count = fields.Integer(
        compute='_compute_vat_relations',
        string="VAT Sale Order Count",
    )
    vat_adjustment_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_vat_relations',
        string="VAT Adjustment Invoices",
    )
    vat_adjustment_invoice_count = fields.Integer(
        compute='_compute_vat_relations',
        string="VAT Adjustment Invoice Count",
    )
    is_import = fields.Boolean(
        string="Is Import",
        default=False,
        index=True,
        states={'posted': [('readonly', True)]},
    )
    settlements_with_customs_account_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        domain="[('company_id', '=', company_id)]",
        string="Settlements with customs",
        compute='_compute_settlements_with_customs_account_id',
        store=True,
        readonly=False,
        states={'posted': [('readonly', True)]},
    )

    @api.depends('move_type')
    @api.onchange('move_type')
    def _compute_default_contract_operation_type(self):
        for rec in self:
            if rec.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice'):
                rec.default_contract_operation_type = 'purchase'
            else:
                super()._compute_default_contract_operation_type()

    # for use in summary control
    vat_summary = fields.Binary(
        compute='_compute_vat_summary'
    )

    @api.depends('vat_line_ids')
    def _compute_vat_summary(self):
        for record in self:
            record.vat_summary = self._calc_vat_summary(record)

    @api.onchange(
        'vat_line_ids',
        'vat_invoice_no_obligation',
        'move_type',
        'is_import',
        'settlements_with_customs_account_id',
        'vat_invoice_not_standard_account_id',
    )
    def _update_vat_lines(self):
        for record in self:
            acc_vat_confirmed_id = record.company_id.vat_account_confirmed_id.id
            if record.vat_invoice_not_standard_account_id:
                acc_vat_unconfirmed_id = record.vat_invoice_not_standard_account_id.id
            else:
                acc_vat_unconfirmed_id = record.company_id.vat_account_unconfirmed_id.id
            acc_vat_credit_unconfirmed_id = record.company_id.vat_account_unconfirmed_credit_id.id
            acc_vat_id = record.company_id.vat_account_id.id

            if record.move_type in VAT_MOVE_TYPES:
                vendor = record.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')
                if vendor:
                    if record.is_import:
                        acc_unconfirmed_id = record.settlements_with_customs_account_id.id
                    else:
                        acc_unconfirmed_id = acc_vat_credit_unconfirmed_id
                else:
                    if record.vat_invoice_no_obligation:
                        acc_unconfirmed_id = acc_vat_confirmed_id
                    else:
                        acc_unconfirmed_id = acc_vat_unconfirmed_id
                vendor_coefficient = -1 if vendor else 1
                vat_summary = self._calc_vat_tax_summary(record)
                vat_sum = 0.0
                update_lines = []

                for line in record.line_ids:
                    if line.account_id.id == acc_unconfirmed_id:
                        tax = line.vat_invoice_tax_id
                        tax_id = tax.id
                        if tax_id:
                            if tax_id in vat_summary:
                                line.balance = vendor_coefficient * vat_summary[tax_id]['vat']
                                vat_sum += vat_summary[tax_id]['vat']
                                del vat_summary[tax_id]
                            else:
                                update_lines.append(fields.Command.delete(line.id))
                    elif line.account_id.id != acc_vat_id:
                        update_lines.append(fields.Command.delete(line.id))

                for vat_id, sum_el in vat_summary.items():
                    vat = self.env['account.tax'].browse(vat_id)
                    update_lines.append(fields.Command.create({
                        'account_id': acc_unconfirmed_id,
                        'balance': vendor_coefficient * sum_el['vat'],
                        'name': vat.name,
                        'display_type': 'tax',
                        'vat_invoice_tax_id': vat_id,
                    }))
                    vat_sum += sum_el['vat']

                vat_found = False
                for line in record.line_ids:
                    if line.account_id.id == acc_vat_id:
                        line.balance = vendor_coefficient * -vat_sum
                        vat_found = True
                        break
                if not vat_found:
                    update_lines.append(fields.Command.create({
                        'account_id': acc_vat_id,
                        'display_type': 'tax',
                        'balance': vendor_coefficient * -vat_sum,
                    }))

                if update_lines:
                    record.update({
                        'line_ids': update_lines,
                    })

    @api.depends('company_id', 'move_type')
    def _compute_journal_id(self):
        for record in self:
            if record.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
                record.journal_id = record.company_id and record.company_id.vat_journal_id or None
            elif record.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice'):
                record.journal_id = record.company_id and record.company_id.vendor_vat_journal_id or None
            else:
                super(AccountMove, record)._compute_journal_id()

    @api.depends('company_id', 'move_type')
    def _compute_suitable_journal_ids(self):
        for rec in self:
            super(AccountMove, rec)._compute_suitable_journal_ids()
            if rec.move_type == 'vat_adjustment_invoice' and rec.company_id and rec.company_id.vat_journal_id:
                rec.suitable_journal_ids += rec.company_id.vat_journal_id
            elif (
                    rec.move_type == 'vendor_vat_adjustment_invoice'
                    and rec.company_id
                    and rec.company_id.vendor_vat_journal_id
            ):
                rec.suitable_journal_ids += rec.company_id.vendor_vat_journal_id

    @api.depends('date', 'company_id')
    def _compute_registration_due_date(self):
        for rec in self:
            if (
                rec.move_type not in ('vat_invoice', 'vat_adjustment_invoice')
                or not rec.company_id
                or not rec.company_id.vat_payer
            ):
                rec.registration_due_date = False
            elif rec.date.day <= 15:
                rec.registration_due_date = date_utils.add(
                    rec.date,
                    months=rec.company_id.vat_reg_terms_1_next_month,
                    day=rec.company_id.vat_reg_terms_1,
                )
            elif rec.date.day > 15:
                rec.registration_due_date = date_utils.add(
                    rec.date,
                    months=rec.company_id.vat_reg_terms_2_next_month,
                    day=rec.company_id.vat_reg_terms_2,
                )
            else:
                rec.registration_due_date = False

    @api.depends('move_type', 'partner_id.vat', 'not_issued_to_customer', 'reason_type')
    def _compute_vat(self):
        for rec in self:
            if rec.not_issued_to_customer and rec.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
                rec.vat = VAT_NON_PAYERS.get(rec.reason_type, '100000000000')
            else:
                rec.vat = rec.partner_id and rec.partner_id.vat or False

    @api.depends('vat_line_ids')
    def _compute_vat_amount(self):
        for entry in self:
            total = 0
            tax = 0
            base = 0
            for line in entry.vat_line_ids:
                total += line.total_without_vat
                tax += line.vat_amount
                base += line.vat_base
            entry.vat_line_total = total + tax
            entry.vat_line_tax = tax
            entry.vat_line_subtotal = total
            entry.vat_line_total_vat_base = base

    @api.depends('vat_line_ids')
    def _compute_vat_tax_totals(self):
        for move in self:
            move.vat_line_tax_totals = move.get_tax_total()

    @api.depends('move_type')
    def _compute_vendor_vat_invoice_type(self):
        for rec in self:
            if rec.move_type == 'vendor_vat_invoice':
                rec.vendor_vat_invoice_type = 'vendor_vat_invoice'
            elif rec.move_type == 'vendor_vat_adjustment_invoice':
                rec.vendor_vat_invoice_type = 'vendor_vat_adjustment_invoice'
            else:
                rec.vendor_vat_invoice_type = None

    @api.onchange('issuance_date')
    def _onchange_issuance_date(self):
        for rec in self:
            if rec.issuance_date and rec.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice'):
                rec.date = rec.issuance_date

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super()._onchange_partner_id()
        for rec in self:
            if (
                    rec.move_type in ('vat_invoice', 'vat_adjustment_invoice')
                    and rec.partner_id
                    and rec.partner_id.vat_non_payer
            ):
                rec.reason_type = '02'
                rec.not_issued_to_customer = True

    @api.onchange('vendor_vat_invoice_type')
    def _inverse_vendor_vat_invoice_type(self):
        for rec in self:
            if rec.vendor_vat_invoice_type == 'vendor_vat_invoice':
                rec.move_type = 'vendor_vat_invoice'
                rec.vendor_vat_invoice_id = None
            elif rec.vendor_vat_invoice_type == 'vendor_vat_adjustment_invoice':
                rec.move_type = 'vendor_vat_adjustment_invoice'
            else:
                rec.vendor_vat_invoice_id = None

    def _compute_vat_relations(self):
        for record in self:
            contracts = None
            sale_orders = None
            vat_adjustment_invoices = None

            if record.move_type in ('vat_invoice', 'vat_adjustment_invoice', 'vendor_vat_invoice', 'vendor_vat_adjustment_invoice'):
                # @TODO: get related contracts
                contracts = record.contract_id

                # @TODO: get related sale orders and check usage vat_sale_order_id or linked_sale_order_id (DEV-787)
                sale_orders = record.vat_sale_order_id

            if record.move_type == 'vat_invoice':
                vat_adjustment_invoices = self.env['account.move'].search(
                    [
                        ('move_type', '=', 'vat_adjustment_invoice'),
                        ('vat_invoice_adjustment_id', '=', record.id),
                    ]
                )

            record.vat_contract_ids = contracts
            record.vat_contract_count = contracts and len(contracts) or 0
            record.vat_sale_order_ids = sale_orders
            record.vat_sale_order_count = sale_orders and len(sale_orders) or 0
            record.vat_adjustment_invoice_ids = vat_adjustment_invoices
            record.vat_adjustment_invoice_count = vat_adjustment_invoices and len(vat_adjustment_invoices) or 0

    def _compute_vat_fully_reconciled(self):
        for rec in self:
            if rec.vat_vendor_reconcilable:
                valid_accounts = [
                    acc for acc in (
                        rec.company_id.vat_account_unconfirmed_id,
                        rec.company_id.vat_account_unconfirmed_credit_id,
                    ) if acc and acc.reconcile
                ]
                vat_lines = rec.line_ids.filtered(
                    lambda ln: ln.balance != 0 and ln.account_id in valid_accounts
                )
                rec.vat_fully_reconciled = vat_lines and all([ln.reconciled and ln.full_reconcile_id for ln in vat_lines]) or False
            else:
                rec.vat_fully_reconciled = False

    def _compute_vat_vendor_reconcilable(self):
        for rec in self:
            rec.vat_vendor_reconcilable = (
                rec.state == 'posted'
                and (
                    (rec.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice'))
                    or (rec.move_type == 'entry' and rec.first_event_source_id)
                )
            )

    @api.depends('move_type', 'is_import')
    @api.onchange('move_type', 'is_import')
    def _compute_settlements_with_customs_account_id(self):
        AccountAccount = self.env['account.account']
        for record in self:
            if record.move_type == 'vendor_vat_invoice' and record.is_import:
                if not record.settlements_with_customs_account_id:
                    record.settlements_with_customs_account_id = AccountAccount.search(
                        [
                            ('company_id', '=', record.company_id.id),
                            ('code', '=', '377100'),
                        ],
                        limit=1,
                    )
            else:
                record.is_import = False
                record.settlements_with_customs_account_id = None

    @api.onchange('not_issued_to_customer')
    def _onchange_not_issued_to_customer(self):
        for rec in self:
            if not rec.not_issued_to_customer:
                rec.reason_type = False

    @api.onchange('consolidated_vat_invoice')
    def _onchange_consolidated_vat_invoice(self):
        for rec in self:
            if not rec.consolidated_vat_invoice:
                rec.consolidated_tax_code = False

    @api.constrains('reason_type', 'not_issued_to_customer')
    def _check_reason_type_not_issued_to_customer(self):
        for rec in self:
            if rec.not_issued_to_customer and not rec.reason_type:
                raise ValidationError(_("Reason type code is required"))

    @api.constrains('consolidated_tax_code', 'consolidated_vat_invoice')
    def _check_consolidated_tax_code_consolidated_vat_invoice(self):
        for rec in self:
            if rec.consolidated_vat_invoice and not rec.consolidated_tax_code:
                raise ValidationError(_("Consolidated Tax Code is required"))

    # This method should be uncommented after NDS released
    # @api.depends('move_type', 'line_ids.amount_residual', 'contract_id')
    # def _compute_payments_widget_to_reconcile_info(self):
    #     super()._compute_payments_widget_to_reconcile_info()
    #
    #     # show unreconciled items with appropriate sale order / purchase order (if defined)
    #     for record in self:
    #         vals = record.invoice_outstanding_credits_debits_widget
    #
    #         if (record.sale_order_count or record.purchase_order_count) and vals and vals.get('content'):
    #             AccountMoveLine = self.env['account.move.line']
    #             sale_orders = record.mapped('line_ids.linked_sale_order_id')
    #             purchase_orders = record.mapped('line_ids.linked_purchase_order_id')
    #             new_content = []
    #
    #             # filter by sale order
    #             for line in vals['content']:
    #                 move_line = AccountMoveLine.browse(line.get('id'))
    #                 if move_line and move_line.linked_sale_order_id in sale_orders:
    #                     new_content.append(line)
    #
    #             # filter by purchase order
    #             for line in vals['content']:
    #                 move_line = AccountMoveLine.browse(line.get('id'))
    #                 if move_line and move_line.linked_purchase_order_id in purchase_orders:
    #                     new_content.append(line)
    #
    #             if not new_content:
    #                 record.invoice_has_outstanding = False
    #                 record.invoice_outstanding_credits_debits_widget = False
    #             else:
    #                 # update unreconciled items
    #                 record.invoice_outstanding_credits_debits_widget['content'] = new_content

    def _post(self, soft=True):
        res = super()._post(soft=soft)

        line_ids = self.mapped('line_ids')
        # force check linked sale orders
        line_ids.check_linked_sale_order()
        # force check linked purchase orders
        line_ids.check_linked_purchase_order()

        return res

    def _update_refs(self):
        for rec in self.filtered(lambda m: m.vat_vendor_reconcilable):
            names = (
                rec.line_ids.mapped('matched_debit_ids.debit_move_id.move_id.first_event_source_id')
                | rec.line_ids.mapped('matched_credit_ids.credit_move_id.move_id.first_event_source_id')
            ).mapped('name')
            rec.ref = ';'.join(names) if names else None

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)

        for move in moves:
            if move.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
                move._onchange_partner_id()

            if move.move_type == 'vat_invoice' and move.company_id.sequence_vat_invoice_id:
                move.name = move.company_id.sequence_vat_invoice_id.next_by_id()
            elif move.move_type == 'vat_adjustment_invoice' and move.company_id.sequence_vat_adjustment_invoice_id:
                move.name = move.company_id.sequence_vat_adjustment_invoice_id.next_by_id()
            elif (
                move.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')
                and move.company_id.sequence_vendor_vat_invoice_id
            ):
                move.name = move.company_id.sequence_vendor_vat_invoice_id.next_by_id()

        moves._update_vat_lines()

        return moves

    def write(self, values):
        if 'state' in values:
            state = values['state']

            for rec in self:
                if rec.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
                    values_for_vat_invoice = values.copy()
                    if state == 'posted':
                        values_for_vat_invoice['vat_invoice_stage'] = 'prepared'
                    elif state == 'cancel':
                        values_for_vat_invoice['vat_invoice_stage'] = 'cancelled'
                    elif state == 'draft':
                        values_for_vat_invoice['vat_invoice_stage'] = 'draft'
                    super(AccountMove, rec).write(values_for_vat_invoice)

                else:
                    super(AccountMove, rec).write(values)

        else:
            super().write(values)

        self._update_vat_lines()

    def action_vat_export_xml(self):
        if self.filtered(lambda r: r.move_type not in ('vat_invoice', 'vat_adjustment_invoice')):
            raise UserError(_("Only VAT invoices and VAT adjustment invoices can be exported to XML"))

        return {
            'type': 'ir.actions.act_url',
            'url': '/account_move/vat/download_xml/%s' % json.dumps(self.ids).replace(' ', ''),
            'target': 'new',
        }

    @api.model
    def action_vat_import_xml(self):
        return {
            'name': _("Vendor VAT Invoices Import"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.vat_invoice.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            },
        }

    def action_show_vat_source(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.first_event_source_id.id,
            'view_mode': 'form',
        }

    def action_show_vat_contracts(self):
        self.ensure_one()
        if self.vat_contract_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Contract"),
                'res_model': self.vat_contract_ids._name,
                'res_id': self.vat_contract_ids.id,
                'view_mode': 'form',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Contracts"),
                'res_model': self.vat_contract_ids._name,
                'domain': [
                    ('id', 'in', self.vat_contract_ids.ids),
                ],
                'view_mode': 'tree,form',
            }

    def action_show_vat_sale_orders(self):
        self.ensure_one()
        if self.vat_sale_order_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Sale Order"),
                'res_model': self.vat_sale_order_ids._name,
                'res_id': self.vat_sale_order_ids.id,
                'view_mode': 'form',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Sale Orders"),
                'res_model': self.vat_sale_order_ids._name,
                'domain': [
                    ('id', 'in', self.vat_sale_order_ids.ids),
                ],
                'view_mode': 'tree,form',
            }

    def action_show_vat_adjustment_invoices(self):
        self.ensure_one()
        if self.vat_adjustment_invoice_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _("VAT Adjustment Invoice"),
                'res_model': self._name,
                'res_id': self.vat_adjustment_invoice_ids.id,
                'view_mode': 'form',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _("VAT Adjustment Invoices"),
                'res_model': self._name,
                'domain': [
                    ('id', 'in', self.vat_adjustment_invoice_ids.ids),
                ],
                'view_mode': 'tree,form',
            }

    def action_create_vat_adjustment_invoice(self):
        self.ensure_one()

        if self.move_type != 'vat_invoice':
            raise UserError(_("Only VAT invoice can be the basis for VAT adjustment invoice"))

        vat_lines = []
        for rec in self.vat_line_ids:
            vat_lines.append(Command.create({
                'product_id': rec.product_id.id,
                'product_uom_id': rec.product_uom_id.id,
                'quantity': rec.quantity,
                'price_unit': rec.price_unit,
                'total_manual': rec.total_manual,
                'vat_tax_id': rec.vat_tax_id.id,
                'benefit_code_id': rec.benefit_code_id.id,
            }))

        return {
            'name': _("Create VAT Adjustment Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'context': {
                'default_move_type': 'vat_adjustment_invoice',
                'default_partner_id': self.partner_id.id,
                'default_contract_id': self.contract_id.id,
                'default_vat_sale_order_id': self.vat_sale_order_id.id,
                'default_vat_invoice_adjustment_id': self.id,
                'default_not_issued_to_customer': self.not_issued_to_customer,
                'default_reason_type': self.reason_type,
                'default_vat_line_ids': vat_lines,
            },
        }

    def action_vat_invoice_reconcile(self):
        self.ensure_one()

        if not (
            self.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')
            or (self.move_type == 'entry' and self.first_event_source_id)
        ):
            raise UserError(_("Only Vendor VAT Invoices/Vendor VAT Adjustment Invoices can be reconciled this way."))

        action_context = {
            'show_mode_selector': False,
            'company_ids': self.company_id.ids,
            'mode': 'suppliers',
            'partner_ids': self.partner_id.ids,
            'active_model': 'account.move.line',
            'active_ids': self.line_ids.ids,
            'vat_invoice': True,
        }

        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """ Switch off additional move lines creation if this is
            price change mode of credit note.
        """
        non_price_change = self.filtered(lambda r: not r.price_change_mode)
        if non_price_change:
            return super(AccountMove, non_price_change)._stock_account_prepare_anglo_saxon_out_lines_vals()
        return []

    def _get_move_display_name(self, show_ref=False):
        self.ensure_one()
        if self.move_type not in (
            'vat_invoice',
            'vat_adjustment_invoice',
            'vendor_vat_invoice',
            'vendor_vat_adjustment_invoice',
        ):
            return super(AccountMove, self)._get_move_display_name(show_ref)

        name = ''
        if self.state == 'draft':
            if self.move_type == 'vat_invoice':
                name += _("Draft VAT Invoice")
            elif self.move_type == 'vat_adjustment_invoice':
                name += _("Draft VAT Adjustment Invoice")
            elif self.move_type == 'vendor_vat_invoice':
                name += _("Draft Vendor VAT Invoice")
            elif self.move_type == 'vendor_vat_adjustment_invoice':
                name += _("Draft Vendor VAT Adjustment Invoice")
            else:
                name += _("Draft Tax Invoice")
            name += ' '
        if not self.name or self.name == '/':
            name += f'(* {self.id})'
        else:
            name += self.name
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'

        return f'{name} ({shorten(self.ref, width=50)})' if show_ref and self.ref else name

    def get_tax_total(self):
        self.ensure_one()
        total_untaxed = 0
        tax = 0
        vat = 0
        vat_base = 0
        groupped = {}
        for line in self.vat_line_ids:

            if line.vat_tax_id:
                taxes = line.tax_before_vat_ids + line.vat_tax_id
                dsc = (100 - (line.discount or 0))/100
                tax_calcs = taxes.compute_all(price_unit=line.price_unit * dsc, quantity=line.quantity)
                total_untaxed += tax_calcs['total_excluded']
                for tax_calc in tax_calcs['taxes']:
                    tax_id = tax_calc['id']
                    if isinstance(tax_id, models.NewId):
                        tax_id = tax_id.origin
                    tax_id = line.env['account.tax'].browse(tax_id)

                    if tax_id.tax_group_id.id in groupped:
                        group_val = groupped[tax_id.tax_group_id.id]
                    else:
                        group_val = {
                            'amount': 0,
                            'base': 0,
                            'is_vat': tax_id.tax_group_id.is_vat,
                            'name': tax_id.tax_group_id.name,
                        }
                        groupped[tax_id.tax_group_id.id] = group_val

                    group_val['amount'] += tax_calc['amount']
                    group_val['base'] += tax_calc['base']
                    tax += tax_calc['amount']
                    if tax_id.tax_group_id.is_vat:
                        vat += tax_calc['amount']
                        vat_base += tax_calc['base']

        groups = []
        for (group_id, group) in groupped.items():
            groups.append({
                'group_key': group_id,
                'tax_group_id': group_id,
                'tax_group_name': group['name'],
                'tax_group_amount': group['amount'],
                'tax_group_base_amount': group['base'],
                'tax_group_is_vat': group['is_vat'],
                'formatted_tax_group_amount': format_grn(self.env, group['amount']),
                'formatted_tax_group_base_amount': format_grn(self.env, group['base']),
            })

        untaxed_name = _("Untaxed Amount")
        other_taxes = _("Other taxes")

        if self.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
            subtotals = [{
                'name': untaxed_name,
                'amount': total_untaxed,
                'formatted_amount': format_grn(self.env, total_untaxed),
            }]
            groups_by_subtotal = {untaxed_name: groups}
            subtotals_order = [untaxed_name]
        else:
            subtotals = []
            groups_by_subtotal = {}
            subtotals_order = []

        return {
            'amount_untaxed': total_untaxed,
            'formatted_amount_untaxed': format_grn(self.env, total_untaxed),
            'amount_total': total_untaxed + tax,
            'formatted_amount_total': format_grn(self.env, total_untaxed + tax),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': subtotals_order,
            'display_tax_base': False,
            'tax_base_total': total_untaxed,
            'formatted_tax_base_total': format_grn(self.env, total_untaxed),
            'tax_total': tax,
            'formatted_tax_total': format_grn(self.env, tax),
            'vat_total': vat,
            'formatted_vat_total': format_grn(self.env, vat),
            'vat_base_total': vat_base,
            'formatted_vat_base_total': format_grn(self.env, vat_base),
        }

    def vat_create_xml(self):
        self.ensure_one()
        if self.move_type not in ('vat_invoice', 'vat_adjustment_invoice'):
            raise UserError(_("Only VAT invoices and VAT adjustment invoices can be exported to XML"))

        # get data
        data = {}
        if self.move_type == 'vat_invoice':
            data = self._get_vat_invoice_data()
        elif self.move_type == 'vat_adjustment_invoice':
            data = self._get_vat_adjustment_invoice_data()

        # render XML
        xml_data = self.env['ir.qweb']._render(
            f'selferp_l10n_ua_vat.account_move_template_export_xml_{self.move_type}',
            {
                'record': self,
                'data': data,
            },
        ).strip()
        xml_data = xml_prettify(xml_data)

        # create file name
        file_name = export_xml_file_name(data)

        # return result
        return file_name, xml_data

    def _get_vat_invoice_data(self):
        """ Prepare data for render VAT Invoice XML

            @see https://wiki.edin.ua/ru/latest/XML/XML-structure.html#declar
        :return:
        """
        self.ensure_one()
        if self.move_type != 'vat_invoice':
            raise UserError(_("Only VAT invoices and VAT adjustment invoices can be exported to XML"))

        # prepare data
        data = self._get_vat_base_xml_data(DOC_VAT_INVOICE)
        data.update({
            # DECLARBODY
            # HEAD
            'R01G1': '1' if self.consolidated_vat_invoice else '0',
            'R03G10S': 'Без ПДВ' if self.composed_of_tax_exempt_transactions else None,

            # BODY
            'R04G11': self.vat_line_total_vat_base + self.vat_line_tax,
            'R03G11': None,         # filled together with RXXXX rows
            'R03G7': None,          # filled together with RXXXX rows
            'R03G109': None,        # filled together with RXXXX rows
            'R03G14': None,         # filled together with RXXXX rows
            'R01G7': None,          # filled together with RXXXX rows
            'R01G109': None,        # filled together with RXXXX rows
            'R01G14': None,         # filled together with RXXXX rows
            'R01G9': None,          # filled together with RXXXX rows
            'R01G8': None,          # filled together with RXXXX rows
            'R01G10': None,         # filled together with RXXXX rows
            'R02G11': None,
        })

        # process lines
        rows = data['RXXXX']
        for line in self.vat_line_ids:
            vat_code = line.vat_tax_id.tax_group_id.vat_code
            amount = line.vat_base

            # update counters depending on VAT tax code
            if vat_code == '20':
                data['R03G11'] = (data['R03G11'] or 0) + line.vat_amount
                data['R03G7'] = (data['R03G7'] or 0) + line.vat_amount
                data['R01G7'] = (data['R01G7'] or 0) + amount
            elif vat_code == '7':
                data['R03G11'] = (data['R03G11'] or 0) + line.vat_amount
                data['R03G109'] = (data['R03G109'] or 0) + line.vat_amount
                data['R01G109'] = (data['R01G109'] or 0) + amount
            elif vat_code == '14':
                data['R03G11'] = (data['R03G11'] or 0) + line.vat_amount
                data['R03G14'] = (data['R03G14'] or 0) + line.vat_amount
                data['R01G14'] = (data['R01G14'] or 0) + amount
            elif vat_code == '901':
                data['R01G9'] = (data['R01G9'] or 0) + amount
            elif vat_code == '902':
                data['R01G8'] = (data['R01G8'] or 0) + amount
            elif vat_code == '903':
                data['R01G10'] = (data['R01G10'] or 0) + amount

            # add row
            rows.append({
                'RXXXXG3S': line.product_id.name or None,
                'RXXXXG4': line.product_id.uktzed_code_id and re.sub('\\s+', '', line.product_id.uktzed_code_id.code or '') or None,
                'RXXXXG32': '1' if line.product_id.is_import_product else None,
                'RXXXXG33': line.product_id.dkpp_code_id and line.product_id.dkpp_code_id.code or None,
                'RXXXXG4S': (line.product_uom_id or line.product_id.uom_id).name,
                'RXXXXG105_2S': (line.product_uom_id or line.product_id.uom_id).code or None,
                'RXXXXG5': export_xml_format_number(line.quantity),
                'RXXXXG6': export_xml_format_number(line.vat_base / line.quantity, min_decimal=2),
                'RXXXXG008': vat_code or None,
                'RXXXXG009': line.benefit_code_id and line.benefit_code_id.code or None,
                'RXXXXG010': export_xml_format_number(amount, min_decimal=2, max_decimal=2),
                'RXXXXG11_10': vat_code not in ('901', '902', '903') and export_xml_format_number(line.vat_amount, min_decimal=2, max_decimal=6) or None,
            })

        # postprocess data
        for name in ('R04G11', 'R03G11', 'R03G7', 'R03G109', 'R03G14', 'R01G7', 'R01G109', 'R01G14', 'R01G9', 'R01G8', 'R01G10', 'R02G11'):
            value = data[name]
            if value is not None:
                data[name] = export_xml_format_number(value, min_decimal=2, max_decimal=2)

        # return result
        return data

    def _get_vat_adjustment_invoice_data(self):
        """ Prepare data for render VAT Adjustment Invoice XML

            @see https://wiki.edin.ua/ru/latest/XML/XML-structure.html#declar
        :return:
        """
        self.ensure_one()
        if self.move_type != 'vat_adjustment_invoice':
            raise UserError(_("Only VAT invoices and VAT adjustment invoices can be exported to XML"))

        # prepare data
        data = self._get_vat_base_xml_data(DOC_VAT_ADJUSTMENT_INVOICE)
        data.update({
            # DECLARBODY
            # HEAD
            'HERPN0': '1' if self.registration_type_adjustment == 'by_vendor' else None,
            'HERPN': '1' if self.registration_type_adjustment == 'by_customer' else None,
            'R01G1': '1' if self.to_consolidated_vat_invoice else '0',
            'R03G10S': 'Без ПДВ' if self.to_vat_invoice_exempt_from_taxation else None,
            # @TODO: reference on VAT Invoice is required (see DEV-775)
            'HPODFILL': self.vat_invoice_adjustment_id and self.vat_invoice_adjustment_id.date.strftime('%d%m%Y') or None,
            'HPODNUM': self.vat_invoice_adjustment_id and int(re.findall(r'(\d+)$', self.vat_invoice_adjustment_id.name)[-1]) or None,
            'HPODNUM1': None,
            'HPODNUM2': None,

            # BODY
            'R001G03': None,        # filled together with RXXXX rows
            'R02G9': None,          # filled together with RXXXX rows
            'R02G111': None,        # filled together with RXXXX rows
            'R03G14': None,         # filled together with RXXXX rows
            'R01G9': None,          # filled together with RXXXX rows
            'R01G111': None,        # filled together with RXXXX rows
            'R01G14': None,         # filled together with RXXXX rows
            'R006G03': None,        # filled together with RXXXX rows
            'R007G03': None,        # filled together with RXXXX rows
            'R01G11': None,         # filled together with RXXXX rows

            'R0301G1D': None,
            'R0301G2': None,
            'R0301G3': None,
            'R0301G4': None,
            'R0301G5': None,
            'R0302G1D': None,
            'R0302G2': None,
            'R0302G3': None,
            'R0302G4': None,
            'R0302G5': None,
        })

        # process lines
        rows = data['RXXXX']
        for line in self.vat_line_ids:
            vat_code = line.vat_tax_id.tax_group_id.vat_code
            amount = line.vat_base

            # update counters depending on VAT tax code
            if vat_code == '20':
                data['R001G03'] = (data['R001G03'] or 0) + line.vat_amount
                data['R02G9'] = (data['R02G9'] or 0) + line.vat_amount
                data['R01G9'] = (data['R01G9'] or 0) + amount
            elif vat_code == '7':
                data['R001G03'] = (data['R001G03'] or 0) + line.vat_amount
                data['R02G111'] = (data['R02G111'] or 0) + line.vat_amount
                data['R01G111'] = (data['R01G111'] or 0) + amount
            elif vat_code == '14':
                data['R001G03'] = (data['R001G03'] or 0) + line.vat_amount
                data['R03G14'] = (data['R03G14'] or 0) + line.vat_amount
                data['R01G14'] = (data['R01G14'] or 0) + amount
            elif vat_code == '901':
                data['R006G03'] = (data['R006G03'] or 0) + amount
            elif vat_code == '902':
                data['R007G03'] = (data['R007G03'] or 0) + amount
            elif vat_code == '903':
                data['R01G11'] = (data['R01G11'] or 0) + amount

            # add row
            line_data = {
                'RXXXXG001': line.adjustment_num_line_vat_invoice,
                'RXXXXG21': line.adjustment_reason_type,
                'RXXXXG22': line.adjustment_group,
                'RXXXXG3S': line.product_id.name or None,
                'RXXXXG4': line.product_id.uktzed_code_id and re.sub('\\s+', '', line.product_id.uktzed_code_id.code or '') or None,
                'RXXXXG32': '1' if line.product_id.is_import_product else None,
                'RXXXXG33': line.product_id.dkpp_code_id and line.product_id.dkpp_code_id.code or None,
                'RXXXXG4S': (line.product_uom_id or line.product_id.uom_id).name,
                'RXXXXG105_2S': (line.product_uom_id or line.product_id.uom_id).code or None,
                'RXXXXG008': vat_code or None,
                'RXXXXG009': line.benefit_code_id and line.benefit_code_id.code or None,
                'RXXXXG010': export_xml_format_number(amount, min_decimal=2, max_decimal=2),
                'RXXXXG11_10': vat_code not in ('901', '902', '903') and export_xml_format_number(line.vat_amount, min_decimal=2, max_decimal=6) or None,
            }

            if line.adjustment_cause_type == 'quantity':
                line_data.update({
                    'RXXXXG5': export_xml_format_number(line.quantity),
                    'RXXXXG6': export_xml_format_number(line.price_without_vat, min_decimal=2),
                })
            elif line.adjustment_cause_type == 'price':
                line_data.update({
                    'RXXXXG7': export_xml_format_number(line.price_without_vat, min_decimal=2),
                    'RXXXXG8': export_xml_format_number(line.quantity),
                })

            rows.append(line_data)

        # postprocess data
        for name in ('R001G03', 'R02G9', 'R02G111', 'R03G14', 'R01G9', 'R01G111', 'R01G14', 'R006G03', 'R007G03', 'R01G11'):
            value = data[name]
            if value is not None:
                data[name] = export_xml_format_number(value, min_decimal=2, max_decimal=2)

        # return result
        return data

    def _get_vat_base_xml_data(self, doc_key):
        self.ensure_one()

        company = self.company_id
        doc_date = self.date
        doc_num = export_xml_extract_doc_number(self.name)

        # get customer/supplier fields
        if self.not_issued_to_customer and self.reason_type == '14':
            customer_vat = '500000000000'
            customer_name = self.partner_id.name
            if self.partner_id.country_id:
                customer_name += ', ' + self.partner_id.country_id.name
            customer_company_registry = self.partner_id.company_registry or None
            customer_branch_number = self.customer_branch_number or None
            customer_company_legal_form = None
            supplier_vat = company.vat
            supplier_name = company.name
            supplier_company_registry = (
                supplier_vat not in ('100000000000', '300000000000', '400000000000', '500000000000', '600000000000')
                and company.company_registry
                or None
            )
            supplier_branch_number = company.branch_number or None

        else:
            customer_vat = company.vat
            customer_name = company.name
            customer_company_registry = company.company_registry or None
            customer_branch_number = company.branch_number or None
            customer_company_legal_form = '2' if company.company_legal_form == 'private' else '1'
            supplier_vat = self.vat
            supplier_name = self.partner_id.name
            supplier_company_registry = (
                supplier_vat not in ('100000000000', '300000000000', '400000000000', '500000000000', '600000000000')
                and self.partner_id.company_registry
                or None
            )
            supplier_branch_number = self.customer_branch_number or None

        vat_type = None
        if supplier_company_registry:
            if len(supplier_company_registry) == 8:
                vat_type = '1'
            elif len(supplier_company_registry) == 12:
                vat_type = '2'

        # prepare data
        data = export_xml_create_base_head(doc_key, company, doc_num, doc_date=doc_date)
        data.update({
            # DECLARBODY

            # HEAD
            # 'R01G1': '0',           # type depended value
            # 'R03G10S': None,        # type depended value
            'HORIG1': '1' if self.not_issued_to_customer else '0',
            'HTYPR': self.reason_type.zfill(2) if self.not_issued_to_customer else None,
            'HFILL': doc_date.strftime('%d%m%Y'),
            'HNUM': doc_num,
            'HNUM1': None,
            'HNAMESEL': customer_name,
            'HNAMEBUY': supplier_name,
            'HKSEL': customer_vat,
            'HNUM2': customer_branch_number,
            'HTINSEL': customer_company_registry,
            'HKS': customer_company_legal_form,
            'HKBUY': supplier_vat,
            'HFBUY': supplier_branch_number,
            'HTINBUY': supplier_company_registry,
            'HKB': vat_type,

            # TABLE №1
            'RXXXX': [],

            # FOOTER
            'HBOS': company.chief_accountant_id and company.chief_accountant_id.name or '',
            'HKBOS': company.chief_accountant_id and company.chief_accountant_id.vat or '',
            'R003G10S': None,
        })

        # return result
        return data

    def _calc_first_event_by_move(self):
        self.ensure_one()
        return self.env['account.vat.calculations']._calc_first_event_by_move(self)

    def _calc_vat_summary(cls, record):
        summary = {}
        for line in record.vat_line_ids:
            taxes = line.tax_before_vat_ids + line.vat_tax_id
            dsc = (100 - (line.discount or 0))/100
            tax_calc = taxes.compute_all(price_unit=line.price_unit * dsc, quantity=line.quantity)
            vat_calc = next(x for x in tax_calc['taxes'] if x['id'] == line.vat_tax_id.id)
            tax_group_id = line.vat_tax_id.tax_group_id.id
            if tax_group_id not in summary:
                summary[tax_group_id] = {'base': 0.0, 'vat': 0.0}
            summary[tax_group_id]['vat'] += vat_calc['amount']
            summary[tax_group_id]['base'] += vat_calc['base']
        return summary

    @classmethod
    def _calc_vat_tax_summary(cls, record):
        summary = {}
        for line in record.vat_line_ids:
            tax_id = line.vat_tax_id.id
            taxes = line.tax_before_vat_ids + line.vat_tax_id
            dsc = (100 - (line.discount if line.discount else 0)) / 100
            tax_calc = taxes.compute_all(price_unit=line.price_unit * dsc, quantity=line.quantity)
            vat_calc = next(x for x in tax_calc['taxes'] if x['id'] == tax_id)
            if tax_id not in summary:
                summary[tax_id] = {'base': 0.0, 'vat': 0.0}
            summary[tax_id]['vat'] += vat_calc['amount']
            summary[tax_id]['base'] += vat_calc['base']
        return summary

    @api.model
    def get_views(self, views, options=None):
        def gen_array_of_refs(array_refs):
            ret = []
            for ref in array_refs:
                real_object = self.env.ref(ref, raise_if_not_found=False)
                if real_object:
                    ret.append(real_object.id)
            return ret

        res = super().get_views(views, options)

        if not options.get('toolbar'):
            return res

        action = None
        if options.get('action_id'):
            action = self.env['ir.actions.actions'].sudo().browse(options['action_id'])
            action = self.env[action.type].sudo().browse(action.id)

        if action:
            if action.xml_id in VAT_ACTIONS:
                to_remove_print_ids = gen_array_of_refs(VAT_ACTIONS_REMOVE_PRINTS)
                to_remove_action_ids = gen_array_of_refs(VAT_ACTIONS_REMOVE_ACTIONS)
            else:
                to_remove_print_ids = []
                to_remove_action_ids = gen_array_of_refs(VAT_ACTIONS_REMOVE_IN_NON_VAT)
        else:
            to_remove_print_ids = []
            to_remove_action_ids = []

        views = res.get('views', {})

        for view_name in ('form', 'list'):
            view = views.get(view_name, {})
            toolbar = view.get('toolbar', {})

            toolbar_print = toolbar.get('print')
            if toolbar_print and to_remove_print_ids:
                toolbar['print'] = [r for r in toolbar_print if r['id'] not in to_remove_print_ids]

            toolbar_action = toolbar.get('action')
            if toolbar_action and to_remove_action_ids:
                toolbar['action'] = [r for r in toolbar_action if r['id'] not in to_remove_action_ids]

        return res

    def is_vat_invoice(self):
        self.ensure_one()
        return self.move_type in [
            'vat_invoice',
            'vat_adjustment_invoice',
            'vendor_vat_invoice',
            'vendor_vat_adjustment_invoice',
        ]

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        for invoice in self:
            if invoice.is_vat_invoice():
                for line in invoice.line_ids:
                    if line.partner_id != invoice.commercial_partner_id:
                        line.partner_id = invoice.commercial_partner_id
                        line._inverse_partner_id()
            else:
                super()._inverse_partner_id()
