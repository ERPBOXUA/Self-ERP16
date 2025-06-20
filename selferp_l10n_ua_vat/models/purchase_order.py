from odoo import api, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'linked_moves.mixin']

    @api.depends('order_line.taxes_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id', 'amount_paid')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        self._update_amount_paid_totals()

    def action_create_invoice(self):
        if len(self) > 1:
            raise UserError(_("Invoice can be created for single purchase order only."))

        return super().action_create_invoice()

    def _get_move_lines_domain(self):
        self.ensure_one()
        return [
            ('move_id.state', '=', 'posted'),
            ('linked_purchase_order_id', '=', self.id),
        ]

    @api.model
    def _get_payment_amount_sign(self):
        return -1
