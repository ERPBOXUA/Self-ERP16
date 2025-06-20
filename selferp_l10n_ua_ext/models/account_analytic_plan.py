from odoo import models, fields


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    active = fields.Boolean(
        default=True,
        string="Active",
    )
    legacy_plan = fields.Boolean(
        default=True,
    )
    plan_template_id = fields.Many2one(
        comodel_name='account.analytic.plan.template',
        string="Plan Template",
        ondelete='set null',
    )

    def _get_default(self):
        plan = self.env['account.analytic.plan'].sudo().search(
            ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id), ('legacy_plan', '=', True)],
            limit=1,
        )
        if plan:
            return plan

        return self.env['account.analytic.plan'].create({
            'name': 'Default',
            'company_id': self.env.company.id,
        })
