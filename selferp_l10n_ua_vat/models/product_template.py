from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_import_product = fields.Boolean(
        string="Import product",
    )
