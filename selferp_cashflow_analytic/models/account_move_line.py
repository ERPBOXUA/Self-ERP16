from odoo import models, fields
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cash_flow_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Cash Flow Analytic Account",
        domain=[('cash_flow_article', '=', True)],
    )

    can_change_cash_flow_analytic_account = fields.Boolean(
        compute='_compute_can_change_cash_flow_analytic_account'
    )

    def _compute_can_change_cash_flow_analytic_account(self):
        for rec in self:
            rec.can_change_cash_flow_analytic_account = (
                rec.account_id
                and rec.account_id.account_type == 'asset_cash'
            )

    def update_cash_flow_analytic_account_id(self, analytic_account_id):
        self.ensure_one()

        prev_analytic_account_id = self.cash_flow_analytic_account_id
        self.cash_flow_analytic_account_id = analytic_account_id

        analytic_distribution = self.analytic_distribution or {}
        if self.cash_flow_analytic_account_id:
            analytic_distribution[str(self.cash_flow_analytic_account_id.id)] = 100.0
        if prev_analytic_account_id:
            analytic_distribution.pop(str(prev_analytic_account_id.id), False)
            self.analytic_distribution = analytic_distribution
        self.analytic_distribution = analytic_distribution

        if self.statement_line_id:
            self.statement_line_id.cash_flow_analytic_account_id = analytic_account_id

        self.analytic_line_ids.unlink()
        self._create_analytic_lines()

    def _prepare_analytic_distribution_line(self, distribution, account_id, distribution_on_each_plan):
        result = super()._prepare_analytic_distribution_line(distribution, account_id, distribution_on_each_plan)

        if result:
            cash_flow_analytic_account = (
                self.move_id
                and self.move_id.statement_line_id
                and self.move_id.statement_line_id.cash_flow_analytic_account_id
            )
            if cash_flow_analytic_account and cash_flow_analytic_account.id == int(account_id):
                amount = result.get('amount')
                if amount and not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    result['amount'] = -amount
                self.cash_flow_analytic_account_id = cash_flow_analytic_account

        return result
