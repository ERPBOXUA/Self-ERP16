from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def get_ua_vat(self):
        self.ensure_one()
        for tax in self.taxes_id.filtered(lambda l: l.tax_group_id.is_vat):
            return tax._compute_amount(self.price_unit * self.product_uom_qty, self.price_unit)
        return 0

    def get_ua_vat_tax(self):
        self.ensure_one()
        for tax in self.taxes_id.filtered(lambda l: l.tax_group_id.is_vat):
            return tax
        return None
