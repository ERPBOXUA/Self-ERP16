from odoo import models, fields, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'address_custom.mixin']

    assembly_location = fields.Char(
        string="Assembly location",
        default=lambda self: self.env.company.city,
    )
