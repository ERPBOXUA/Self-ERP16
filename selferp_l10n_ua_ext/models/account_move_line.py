from odoo import api, models, fields, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('display_type', 'move_type')
    def _compute_quantity(self):
        for line in self:
            if line.display_type == 'product' and line.move_type != 'entry':
                line.quantity = line.quantity if line.quantity else 1
            else:
                line.quantity = False
