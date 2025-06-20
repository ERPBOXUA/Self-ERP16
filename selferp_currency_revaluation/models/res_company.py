from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_revaluation_reverse_type = fields.Selection(
        selection=[
            ('reverse', "Reverse"),
            ('storno', "Storno"),
        ],
        default='storno',
    )
