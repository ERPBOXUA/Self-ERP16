from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'linked_moves.mixin']

    vat_invoices = fields.One2many(
        string="VAT invoices",
        comodel_name='account.move',
        inverse_name='vat_sale_order_id',
    )

    vat_invoice_total = fields.Monetary(
        string="Total VAT Invoice",
        compute='_compute_vat_invoice_total',
    )

    vat_invoices_summary = fields.Binary(
        string="Product summary by VAT invoices",
        compute='_compute_vat_invoices_summary',
    )

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id', 'amount_paid')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        self._update_amount_paid_totals()

    def _compute_vat_invoice_total(self):
        for rec in self:
            rec.vat_invoice_total = sum(
                self.env['account.move']
                    .search(
                        domain=[
                            ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
                            ('vat_sale_order_id', '=', rec.id),
                        ],
                    )
                    .mapped('vat_line_total')
            )

    @api.depends('vat_invoices', 'vat_invoices.vat_line_ids')
    def _compute_vat_invoices_summary(self):
        for rec in self:
            summary = {}
            for invoice in rec.vat_invoices:
                if invoice.move_type in ['vat_invoice', 'vat_adjustment_invoice']:
                    for vat_line in invoice.vat_line_ids:
                        key = (
                            vat_line.product_id.id,
                            vat_line.product_uom_id.id,
                            vat_line.price_unit,
                            vat_line.discount,
                            vat_line.vat_tax_id.id,
                        )
                        value = summary.get(key)
                        if not value:
                            value = {
                                'qty': 0.0,
                                'vat': 0.0,
                            }
                            summary[key] = value
                        value['qty'] += vat_line.quantity
                        value['vat'] += vat_line.vat_amount
            rec.vat_invoices_summary = summary

    def action_view_vat_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("VAT Invoices"),
            'res_model': 'account.move',
            'domain': [
                ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
                ('vat_sale_order_id', '=', self.id),
            ],
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('selferp_l10n_ua_vat.account_move_view_tree_vat_invoice').id, 'tree'),
                (False, 'form'),
            ],
            'search_view_id': [self.env.ref('selferp_l10n_ua_vat.account_move_view_search_vat_invoice').id, 'search'],
        }

    def get_line_summary(self, line):
        self.ensure_one()
        if not line.get_ua_vat_tax():
            return None
        key = (
            line.product_id.id,
            line.product_uom.id,
            line.price_unit,
            line.discount,
            line.get_ua_vat_tax().id,
        )
        return self.vat_invoices_summary.get(key)

    def _get_move_lines_domain(self):
        self.ensure_one()
        return [
            ('move_id.state', '=', 'posted'),
            ('linked_sale_order_id', '=', self.id),
        ]

    @api.model
    def _get_payment_amount_sign(self):
        return 1
