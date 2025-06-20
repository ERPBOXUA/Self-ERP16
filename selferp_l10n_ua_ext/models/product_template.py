from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uktzed_code_id = fields.Many2one(
        comodel_name='product.uktzed_code',
        ondelete='restrict',
        domain=[('visible', '=', True), ('selectable', '=', True)],
        string="UKTZED Code",
        help="Code of the ukrainian classification of products for foreign economic activity",
    )

    dkpp_code_id = fields.Many2one(
        comodel_name='product.dkpp_code',
        ondelete='restrict',
        string="DKPP Code",
        help="Code for Ukrainian State classifier of products and services",
    )
