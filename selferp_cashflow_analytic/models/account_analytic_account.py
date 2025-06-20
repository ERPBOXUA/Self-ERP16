from odoo import models, fields


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _order = 'code, name'

    cash_flow_article = fields.Boolean(
        string="Cash Flow Article",
        related='plan_id.cash_flow_article',
        store=True,
    )
