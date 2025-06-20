from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_salary_advance_calculation = fields.Selection(
        related='company_id.salary_advance_calculation',
        readonly=False,
    )

    company_salary_advance_percents = fields.Float(
        related='company_id.salary_advance_percents',
        readonly=False,
    )

    company_salary_indexation_period_ids = fields.One2many(
        related='company_id.salary_indexation_period_ids',
        readonly=False,
    )
