from odoo import models, fields, api


class HrScheduleLine(models.Model):
    _name = 'hr.schedule.line'
    _description = "Staff Schedule Line"

    schedule_id = fields.Many2one(
        comodel_name='hr.schedule',
        ondelete='cascade',
        string="Staff Schedule",
        required=True,
    )

    job_id = fields.Many2one(
        comodel_name='hr.job',
        ondelete='restrict',
        string="Job Position",
        required=True,
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        ondelete='restrict',
        string="Department",
    )

    employee_qty = fields.Integer(
        string="Number Of Employees",
        default=1,
    )

    salary = fields.Monetary(
        string="Salary",
        currency_field='company_currency_id',
    )

    surcharge = fields.Monetary(
        string="Surcharge",
        currency_field='company_currency_id',
    )

    total_salary = fields.Monetary(
        string="Total Salary",
        currency_field='company_currency_id',
        compute='_compute_total_salary',
    )

    schedule_company_id = fields.Many2one(
        related='schedule_id.company_id',
    )

    company_currency_id = fields.Many2one(
        related='schedule_company_id.currency_id',
    )

    @api.depends('employee_qty', 'salary', 'surcharge')
    @api.onchange('employee_qty', 'salary', 'surcharge')
    def _compute_total_salary(self):
        for rec in self:
            rec.total_salary = (rec.employee_qty or 1) * ((rec.salary or 0.0) + (rec.surcharge or 0.0))

    @api.onchange('employee_qty')
    def _onchange_employee_qty(self):
        for rec in self:
            if not rec.employee_qty or rec.employee_qty <= 0:
                rec.employee_qty = 1
