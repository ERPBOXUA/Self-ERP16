from odoo import models, fields


class HrEmployeeSickLeaveRate(models.Model):
    _name = 'hr.employee.sick_leave.rate'
    _description = "Employee Sick Leave Rates"
    _order = 'employee_id, apply_date desc'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        required=True,
        index=True,
        ondelete='cascade',
    )

    apply_date = fields.Date(
        string="Date",
        required=True,
        index=True,
    )

    sick_leave_rate_id = fields.Many2one(
        comodel_name='hr.salary.sick_leave.rate',
        string="Rate",
        required=True,
        ondelete='restrict',
    )
