from odoo import models, fields


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    price_change_mode = fields.Boolean(
        string="Price Change",
        default=False,
    )

    def _prepare_default_values(self, move):
        result = super()._prepare_default_values(move)
        result.update({
            'price_change_mode': self.price_change_mode,
        })
        return result

