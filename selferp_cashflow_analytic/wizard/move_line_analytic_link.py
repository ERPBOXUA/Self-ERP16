from odoo import models, fields


class AccountMoveLineAnalyticLink(models.TransientModel):
    _name = 'account.move.line.analytic.link'
    _description = "Select Cash Flow Analytic Account"

    move_line_id = fields.Many2one(
        comodel_name='account.move.line',
    )
    cash_flow_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Cash Flow Analytic Account",
        domain=[('cash_flow_article', '=', True)],
    )

    def action_select_analytic_account(self):
        self.ensure_one()
        if self.move_line_id:
            self.move_line_id.update_cash_flow_analytic_account_id(self.cash_flow_analytic_account_id)
