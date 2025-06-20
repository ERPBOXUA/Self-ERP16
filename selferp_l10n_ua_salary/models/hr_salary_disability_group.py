from odoo import models, fields, api, _


class HrSalaryDisabilityGroup(models.Model):
    _name = 'hr.salary.disability_group'
    _description = "Disability Groups"

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', "Name must be unique"),
        ('code_uniq', 'UNIQUE (code)', "Code must be unique"),
    ]

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
    )

    def name_get(self):
        return [(rec.id, '[%s] %s' % (rec.code, rec.name)) for rec in self]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        if not default.get('code'):
            default['code'] = _("%s.copy") % (self.code or '')
        return super().copy(default)
