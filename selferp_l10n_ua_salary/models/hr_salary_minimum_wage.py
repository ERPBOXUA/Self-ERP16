from odoo import models, fields


class HrSalaryMinimumWage(models.Model):
    _name = 'hr.salary.minimum_wage'
    _description = "Minimum Wage"
    _order = 'date desc'
    _rec_name = 'date'

    _sql_constraints = [
        ('date_uniq', 'UNIQUE (date)', "Date must be unique"),
        ('check_minimum_wage_hourly_positive', 'CHECK (value_hourly > 0.0)', "Hourly minimum wage must be greater than zero"),
        ('check_minimum_wage_monthly_positive', 'CHECK (value_monthly > 0.0)', "Monthly minimum wage must be greater than zero"),
    ]

    date = fields.Date(
        string="Date",
        required=True,
        index=True,
    )

    value_hourly = fields.Float(
        string="Minimum Wage (Hourly)",
        required=True,
        digits='Payroll',
    )

    value_monthly = fields.Float(
        string="Minimum Wage (Monthly)",
        required=True,
        digits='Payroll',
    )
