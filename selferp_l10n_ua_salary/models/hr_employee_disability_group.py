from odoo import models, fields


class HrEmployeeDisabilityGroup(models.Model):
    _name = 'hr.employee.disability_group'
    _description = "Employee Disability Groups"
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

    disability_group_id = fields.Many2one(
        comodel_name='hr.salary.disability_group',
        string="Disability Group",
        required=True,
        ondelete='restrict',
    )
