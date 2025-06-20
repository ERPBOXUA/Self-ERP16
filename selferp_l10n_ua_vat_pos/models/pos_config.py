from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    vat_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Default VAT Partner",
    )
