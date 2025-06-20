from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        domain="[('partner_id', '=', partner_id), ('operation_type', '=', 'sale')]",
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped, final, date)

        for move in moves:
            move.contract_id = self.contract_id
            for line in move.line_ids:
                if line.account_id and line.account_id.account_type == 'asset_receivable':
                    line.contract_id = self.contract_id

        return moves
