from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        super()._action_done()

        existing_stock_move_lines = self.exists()
        for move_line in existing_stock_move_lines:
            if move_line.move_id.picking_id and move_line.move_id.picking_id.accounting_date:
                move_line.date = move_line.move_id.picking_id.accounting_date
