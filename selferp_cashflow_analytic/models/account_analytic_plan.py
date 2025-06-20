from odoo import models, fields


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    cash_flow_article = fields.Boolean(
        string="Cash Flow Item",
        default=False,
    )
