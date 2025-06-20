from odoo import fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'

    code = fields.Char(string="Code", index=True, copy=False)
