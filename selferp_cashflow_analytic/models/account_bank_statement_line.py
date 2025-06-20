from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    cash_flow_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Cash Flow Analytic Account",
        domain=[('cash_flow_article', '=', True)],
        check_company=True,
    )
