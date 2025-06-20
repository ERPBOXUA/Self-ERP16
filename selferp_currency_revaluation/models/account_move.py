from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    currency_revaluation = fields.Boolean(
        default=False,
        index=True,
        copy=False,
    )
