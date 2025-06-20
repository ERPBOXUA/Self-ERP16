from odoo import models, fields, api, _

PRECISION_SICK_LEAVE_RATE = (16, 3)


class HrSalarySickLeaveRate(models.Model):
    _name = 'hr.salary.sick_leave.rate'
    _description = "Sick Leave Rates"

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', "Name must be unique"),
        ('check_rate_greater_than_zero', 'CHECK (rate > 0.0)', "The rate must be greater than zero"),
    ]

    name = fields.Char(
        string="Name",
        required=True,
    )

    rate = fields.Float(
        string="Rate",
        required=True,
        digits=PRECISION_SICK_LEAVE_RATE,
    )

    def name_get(self):
        return [(rec.id, '%.1f%% (%s)' % (rec.rate * 100, rec.name)) for rec in self]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        return super().copy(default)
