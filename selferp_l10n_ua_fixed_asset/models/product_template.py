from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(
        selection_add=[('assets', "Assets")],
        ondelete={'assets': 'set service'},
    )
    type = fields.Selection(
        selection_add=[('assets', "Assets")],
        ondelete={'assets': 'set service'},
    )

    @api.onchange('detailed_type')
    def _onchange_detailed_type(self):
        for record in self:
            if record.detailed_type == 'assets':
                record.purchase_method = 'purchase'
