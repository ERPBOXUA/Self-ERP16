from odoo import api, models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    price_change_mode = fields.Boolean(
        string="Price Change",
        default=False,
    )

    @api.onchange('refund_method')
    def _onchange_refund_method(self):
        for record in self:
            record.price_change_mode = False

    def _prepare_default_reversal(self, move):
        result = super()._prepare_default_reversal(move)
        result.update({
            'price_change_mode': self.refund_method == 'refund' and self.price_change_mode,
        })
        return result

