from odoo import models, fields


PRECISION_INFLATION_INDEX = (16, 3)


class HrSalaryInflationIndex(models.Model):
    _name = 'hr.salary.inflation_index'
    _description = "Inflation Indices"
    _order = 'date desc'
    _rec_name = 'date'

    _sql_constraints = [
        ('date_uniq', 'UNIQUE (date)', "Date must be unique"),
        ('check_value_greater_than_zero', 'CHECK(value > 0.0)', "The value must be greater than zero"),
    ]

    date = fields.Date(
        string="Date",
        required=True,
        index=True,
    )

    value = fields.Float(
        string="Value",
        required=True,
        digits=PRECISION_INFLATION_INDEX,
    )
