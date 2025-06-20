from odoo import models, fields


class AccountAnalyticAccountTemplate(models.Model):
    _name = 'account.analytic.account.template'
    _description = "Analytic account template"

    name = fields.Char(
        index='trigram',
        required=True,
        string="Analytic Account",
    )
    code = fields.Char(
        index='btree',
        string="Reference",
    )
    description = fields.Text(
        string="Description",
    )
    plan_template_id = fields.Many2one(
        comodel_name='account.analytic.plan.template',
        required=True,
        ondelete='cascade',
        string="Plan Template",
    )
