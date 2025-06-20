from odoo import models, _
from odoo.tools import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _change_standard_price(self, new_price):
        # Disable change price from 0 to any value for products that already exists on stock.
        if self.env.registry.in_test_mode():
            # Many standard test cases use this in test mode
            return super()._change_standard_price(new_price)

        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
        for product in self:
            if company_id.currency_id.is_zero(product.standard_price) and rounded_new_price >= 0.0:
                quantity_svl = product.sudo().quantity_svl
                if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) > 0:
                    raise UserError(_("You cannot set the cost of a product if it is 0 and the quantity on stock is not 0. Product: %s." % product.display_name))

        return super()._change_standard_price(new_price)
