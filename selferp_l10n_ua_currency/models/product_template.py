from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    split_method_landed_cost = fields.Selection(
        selection_add=[
            ('by_custom_declaration', "By custom declaration"),
        ],
        ondelete={
            'by_custom_declaration': 'cascade',
        },
    )
