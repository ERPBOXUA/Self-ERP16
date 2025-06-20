from odoo import models, fields, api, _


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    timesheet_ccode = fields.Char(
        string="Character Code",
    )

    timesheet_ncode = fields.Integer(
        string="Number Code",
    )

    overtime = fields.Boolean(
        string="Overtime",
        default=False,
    )

    surcharge_percents = fields.Float(
        string="Surcharge",
    )

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('code'):
            default['code'] = _("%s.copy", self.code)
        return super().copy(default)
