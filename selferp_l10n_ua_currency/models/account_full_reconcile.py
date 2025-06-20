from odoo import models


class AccountFullReconcile(models.Model):
    _inherit = 'account.full.reconcile'

    def unlink(self):
        if not self:
            return True

        # Remove exchange difference instead of reversing
        exchange_moves = self.mapped('exchange_move_id')
        if exchange_moves:
            self.write({
                'exchange_move_id': None,
            })
            exchange_moves.filtered(lambda r: r.state == 'posted').button_draft()
            exchange_moves.unlink()

        # then call super
        new_self = self.exists()
        if new_self:
            return super(AccountFullReconcile, new_self).unlink()
