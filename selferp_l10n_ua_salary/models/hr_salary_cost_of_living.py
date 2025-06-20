from odoo import models, fields


class HrSalaryCostOfLiving(models.Model):
    _name = 'hr.salary.cost_of_living'
    _description = "Cost Of Living"
    _order = 'date desc'
    _rec_name = 'date'

    _sql_constraints = [
        ('date_uniq', 'UNIQUE (date)', "Date must be unique"),
        ('check_value_greater_than_zero', 'CHECK(value > 0.0)', "The value must be greater than zero"),
        ('check_value_under_6_greater_than_zero', 'CHECK(value_children_under_6 > 0.0)', "The value for children under 6 y.o. must be greater than zero"),
        ('check_value_6_to_18_greater_than_zero', 'CHECK(value_children_from_6_to_18 > 0.0)', "The value for children From 6 To 18 y.o. must be greater than zero"),

    ]

    date = fields.Date(
        string="Date",
        required=True,
        index=True,
    )

    value = fields.Float(
        string="Value",
        required=True,
        digits='Payroll',
    )

    value_children_under_6 = fields.Float(
        string="Value For Children Under 6 y.o.",
        required=True,
        digits='Payroll',
    )

    value_children_from_6_to_18 = fields.Float(
        string="Value For Children From 6 To 18 y.o.",
        required=True,
        digits='Payroll',
    )
