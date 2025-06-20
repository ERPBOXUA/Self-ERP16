from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

from odoo.addons.selferp_l10n_ua_salary.models.hr_payslip import PAYSLIP_TYPES
from odoo.addons.selferp_l10n_ua_salary.models.res_company import SALARY_ADVANCE_VARIANTS, PRECISION_SALARY_ADVANCE_PERCENTAGE


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    payment_type = fields.Selection(
        selection=PAYSLIP_TYPES,
        string="Payment Type",
        required=True,
        default='salary',
        states={'draft': [('readonly', False)]},
    )

    salary_advance_calculation = fields.Selection(
        selection=SALARY_ADVANCE_VARIANTS,
        string="Salary Advance Calculation",
        default=lambda self: self.env.company.salary_advance_calculation,
        states={'draft': [('readonly', False)]},
    )

    salary_advance_percents = fields.Float(
        string="Salary Percentage",
        digits=PRECISION_SALARY_ADVANCE_PERCENTAGE,
        default=lambda self: self.env.company.salary_advance_percents,
        states={'draft': [('readonly', False)]},
    )

    @api.onchange('date_start')
    def _compute_date_end(self):
        next_month = relativedelta(months=+1, day=1, days=-1)
        for rec in self:
            rec.date_end = rec.date_start and rec.date_start + next_month

    def action_generate_payslips(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_payroll.action_hr_payslip_by_employees')
        context = dict(self.env.context)
        context['payslip_run_id'] = self.id
        action['context'] = context
        return action

    def action_create_payments(self):
        # show created bank statement lines
        return self.env['hr.payslip.create_payment'].create_and_show(self.mapped('slip_ids'))
