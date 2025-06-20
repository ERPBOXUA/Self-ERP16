from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    order_is_import = fields.Boolean(related='order_id.is_import')
