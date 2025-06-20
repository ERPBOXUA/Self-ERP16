from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


SEQUENCES = {
    'sequence_vat_invoice_id': 'selferp_l10n_ua_vat.seq_account_move_vat_invoice',
    'sequence_vat_adjustment_invoice_id': 'selferp_l10n_ua_vat.seq_account_move_vat_adjustment_invoice',
    'sequence_vendor_vat_invoice_id': 'selferp_l10n_ua_vat.seq_account_move_vendor_vat_invoice',
    'sequence_vat_tax_report_id': 'selferp_l10n_ua_vat.seq_account_vat_tax_report',
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_number = fields.Char(
        string="Numerical number of the company's branch",
    )

    vat_payer = fields.Boolean(
        string="VAT Payer",
        default=False,
        index=True,
        copy=False,
    )

    vat_account_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="VAT Account",
    )
    vat_account_unconfirmed_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Unconfirmed VAT Liabilities",
    )
    vat_account_confirmed_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Confirmed VAT Liabilities",
    )

    vat_account_unconfirmed_credit_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Unconfirmed VAT Credit",
    )
    vat_account_confirmed_credit_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Confirmed VAT Credit",
    )

    vat_journal_id = fields.Many2one(
        comodel_name='account.journal',
        ondelete='restrict',
        string="VAT Liabilities Journal",
    )

    first_event_journal_id = fields.Many2one(
        comodel_name='account.journal',
        ondelete='restrict',
        string="First Event VAT Journal",
    )

    vat_default_tax_id = fields.Many2one(
        comodel_name='account.tax',
        ondelete='restrict',
        domain=[('type_tax_use', '=', 'sale'), ('tax_group_id.is_vat', '=', True)],
        string="Sales Tax",
    )
    vat_default_tax_credit_id = fields.Many2one(
        comodel_name='account.tax',
        ondelete='restrict',
        domain=[('type_tax_use', '=', 'purchase'), ('tax_group_id.is_vat', '=', True)],
        string="Purchase Tax",
    )

    vat_default_product_id = fields.Many2one(
        comodel_name='product.product',
        ondelete='restrict',
        string="Default Product",
    )

    vat_reg_terms_1 = fields.Integer(
        string="From 1 to 15 day",
        default=31,
    )
    vat_reg_terms_1_next_month = fields.Boolean(
        default=False,
    )
    vat_reg_terms_2 = fields.Integer(
        string="From 16 to end of month",
        default=15,
    )
    vat_reg_terms_2_next_month = fields.Boolean(
        default=True,
    )

    vendor_vat_journal_id = fields.Many2one(
        comodel_name='account.journal',
        ondelete='restrict',
        string="VAT Credit Journal",
    )

    sequence_vat_invoice_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of VAT Invoices",
    )
    sequence_vat_adjustment_invoice_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of VAT Adjustment Invoices",
    )
    sequence_vendor_vat_invoice_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of Vendor VAT Invoices",
    )
    sequence_vat_tax_report_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of VAT Tax Report",
    )

    @api.constrains('vat_reg_terms_1', 'vat_reg_terms_2')
    def _check_vat_reg_terms(self):
        for record in self:
            if record.vat_reg_terms_1 is not None and (record.vat_reg_terms_1 < 1 or record.vat_reg_terms_1 > 31):
                raise ValidationError(_("The value of day of the month must be a number between 1 and 31 (including)"))
            if record.vat_reg_terms_2 is not None and (record.vat_reg_terms_2 < 1 or record.vat_reg_terms_2 > 31):
                raise ValidationError(_("The value of day of the month must be a number between 1 and 31 (including)"))

    @api.model_create_multi
    def create(self, vals_list):
        # create companies
        companies = super().create(vals_list)

        # setup sequences
        companies._setup_vat_sequences()

        return companies

    def unlink(self):
        # remove sequences
        self.mapped('sequence_vat_invoice_id').unlink()
        self.mapped('sequence_vat_adjustment_invoice_id').unlink()
        self.mapped('sequence_vendor_vat_invoice_id').unlink()
        self.mapped('sequence_vat_tax_report_id').unlink()

        # remove companies
        return super().unlink()

    def get_vat_default_accounts(self):
        self.ensure_one()

        AccountAccount = self.env['account.account']

        vat_account = AccountAccount.search([
            ('company_id', '=', self.id),
            ('code', '=', '641200'),
        ], limit=1)
        vat_account_unconfirmed = AccountAccount.search([
            ('company_id', '=', self.id),
            ('code', '=', '643200'),
        ], limit=1)
        vat_account_confirmed = AccountAccount.search([
            ('company_id', '=', self.id),
            ('code', '=', '643100'),
        ], limit=1)
        vat_account_unconfirmed_credit = AccountAccount.search([
            ('company_id', '=', self.id),
            ('code', '=', '644200'),
        ], limit=1)
        vat_account_confirmed_credit = AccountAccount.search([
            ('company_id', '=', self.id),
            ('code', '=', '644100'),
        ], limit=1)

        if vat_account_unconfirmed_credit and not vat_account_unconfirmed_credit.reconcile:
            vat_account_unconfirmed_credit.reconcile = True

        return (
            vat_account,
            vat_account_unconfirmed,
            vat_account_confirmed,
            vat_account_unconfirmed_credit,
            vat_account_confirmed_credit,
        )

    def get_vat_default_taxes(self):
        self.ensure_one()

        vat_default_tax = self.env['account.tax'].search([
            ('company_id', '=', self.id),
            ('type_tax_use', '=', 'sale'),
            ('price_include', '!=', True),
            ('tax_group_id.is_vat', '=', True),
            ('tax_group_id.vat_code', '=', '20'),
        ], limit=1)
        vat_default_tax_credit = self.env['account.tax'].search([
            ('company_id', '=', self.id),
            ('type_tax_use', '=', 'purchase'),
            ('price_include', '!=', True),
            ('tax_group_id.is_vat', '=', True),
            ('tax_group_id.vat_code', '=', '20'),
        ], limit=1)

        return vat_default_tax, vat_default_tax_credit

    def _setup_vat_sequences(self):
        for field_name, template in SEQUENCES.items():
            without_sequence = self.filtered(lambda r: not r[field_name])

            if without_sequence:
                sequence = self.env.ref(template, raise_if_not_found=False)
                if sequence:
                    for record in without_sequence:
                        record[field_name] = sequence.copy({
                            'company_id': record.id,
                        })
