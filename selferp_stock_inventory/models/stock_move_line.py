from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    stock_inventory_line_id = fields.Many2one(
        comodel_name='stock.inventory.line',
        index=True,
    )
