from odoo import models, fields, api, _
from odoo.tools import get_lang


class AccountContract(models.Model):
    _name = 'account.contract'
    _description = "Contract"

    name = fields.Char(
        string="Name",
        required=True,
        default='/',
    )
    external_name = fields.Char(
        string="External name",
    )
    active = fields.Boolean(default=True)

    operation_type = fields.Selection(
        string="Operation type",
        selection=[
            ('sale', "Sale"),
            ('purchase', "Purchase"),
        ],
        required=True,
        index=True,
    )

    subtype = fields.Selection(
        selection=[
            ('main', "Main"),
            ('additional', "Additional"),
        ],
        default='main',
        index=True,
    )
    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Main contract",
        domain="[('subtype', '=', 'main'), ('partner_id', '=', partner_id)]",
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        copy=False,
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    date_start = fields.Date(
        string="Begin date",
    )
    date_end = fields.Date(
        string="End date",
    )
    is_perpetual = fields.Boolean(
        string="Perpetual",
        default=False,
    )

    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment term",
    )

    move_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='contract_id',
    )
    move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='contract_id',
    )
    move_line_count = fields.Integer(
        compute='_compute_move_line_count',
    )

    invoice_count = fields.Integer(
        string="Invoice Count",
        compute='_compute_invoices',
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_invoices',
    )

    bill_count = fields.Integer(
        string="Bill Count",
        compute='_compute_bills',
    )
    bill_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_bills',
    )

    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='contract_id',
    )
    purchase_order_count = fields.Integer(
        compute='_compute_purchase_order_count',
    )

    sale_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='contract_id',
    )
    sale_order_count = fields.Integer(
        compute='_compute_sale_order_count',
    )

    @api.depends('move_ids')
    def _compute_invoices(self):
        for rec in self:
            invoices = rec.move_ids.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)

    @api.depends('move_ids')
    def _compute_bills(self):
        for rec in self:
            invoices = rec.move_ids.filtered(lambda r: r.move_type in ('in_invoice', 'in_refund'))
            rec.bill_ids = invoices
            rec.bill_count = len(invoices)

    @api.depends('move_line_ids')
    def _compute_move_line_count(self):
        for rec in self:
            rec.move_line_count = len(rec.move_line_ids)

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            c_type = val.get('operation_type') or self._context.get('default_operation_type') or 'sale'
            seq_name = 'account.contract.sequence.purchase' if c_type == 'purchase' else 'account.contract.sequence.sale'
            name = self.env['ir.sequence'].next_by_code(seq_name)

            # Workaround for quick create
            if not val.get('name') or val['name'] == '/':
                val['name'] = name
                val['external_name'] = name
            else:
                val['external_name'] = val['name']
                val['name'] = name

        return super().create(vals_list)

    def name_get(self):
        return [
            (r.id, '%s%s' % (r.external_name or r.name, r.date_start and _(" of %s") % r.date_start.strftime(get_lang(self.env).date_format) or ''))
            for r in self
        ]

    def action_view_invoice(self):
        self.ensure_one()

        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')

        invoices = self.invoice_ids
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        else:
            action.update({
                'res_id': invoices.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })

        action['context'] = {
            'default_move_type': 'out_invoice',
            'default_contract_id': self.id,
            'default_partner_id': self.partner_id.id,
        }

        return action

    def action_view_bill(self):
        self.ensure_one()

        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice_type')

        invoices = self.bill_ids
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        else:
            action.update({
                'res_id': invoices.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })

        action['context'] = {
            'default_move_type': 'in_invoice',
            'default_contract_id': self.id,
            'default_partner_id': self.partner_id.id,
        }

        return action

    def action_view_journal_items(self):
        self.ensure_one()
        return {
            'name': _("Journal Items"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': [('contract_id', '=', self.id)],
            'view_mode': 'tree,pivot,graph,kanban',
        }

    def action_view_purchase_orders(self):
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')

        orders = self.purchase_order_ids
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        else:
            action.update({
                'res_id': orders.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })

        action['context'] = {
            'default_contract_id': self.id,
            'default_partner_id': self.partner_id.id,
        }

        return action

    def action_view_sale_orders(self):
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('sale.act_res_partner_2_sale_order')

        orders = self.sale_order_ids
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        else:
            action.update({
                'res_id': orders.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })

        action['context'] = {
            'default_contract_id': self.id,
            'default_partner_id': self.partner_id.id,
        }

        return action
