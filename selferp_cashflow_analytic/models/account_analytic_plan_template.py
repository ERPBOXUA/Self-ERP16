from odoo import models, fields


class AccountAnalyticPlanTemplate(models.Model):
    _inherit = 'account.analytic.plan.template'

    cash_flow_article = fields.Boolean(
        default=False,
        string="Cash Flow Item",
    )

    def _get_plan_vals(self, company, parent_id):
        self.ensure_one()

        plan_vals = super()._get_plan_vals(company, parent_id)

        if self.cash_flow_article:
            plan_vals['cash_flow_article'] = True

        return plan_vals
