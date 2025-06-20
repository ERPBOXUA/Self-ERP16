from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def create_invoice_delivered(self):
        self._create_invoices()
        return self.action_view_invoice()
