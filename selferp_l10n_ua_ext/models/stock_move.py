from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)

        for move in moves:
            if move.picking_id and move.picking_id.accounting_date:
                move.date = move.picking_id.accounting_date

        return moves
