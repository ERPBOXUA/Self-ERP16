from odoo import models, fields, api, Command, _


class HrEmployeeFamily(models.Model):
    _name = 'hr.employee.family'
    _description = "Employee Family"

    family_id = fields.Many2one(
        comodel_name='hr.employee',
        ondelete='cascade',
        string="Family",
    )

    family_member = fields.Char(
        string="Family member",
    )

    family_member_name = fields.Char(
        string="Family member name",
    )

    family_member_birth_date = fields.Date(
        string="Birth date",
    )

    family_member_phone = fields.Char(
        string="Phone",
    )
