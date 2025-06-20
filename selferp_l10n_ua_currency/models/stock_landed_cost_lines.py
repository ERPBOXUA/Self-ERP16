from odoo import fields, models


class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(
        selection_add=[
            ('by_custom_declaration', "By custom declaration"),
        ],
        ondelete={
            'by_custom_declaration': 'cascade',
        }
    )
