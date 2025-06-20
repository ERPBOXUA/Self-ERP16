from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import float_compare


PRECISION_TAX_SOCIAL_BENEFIT_RATE = (16, 3)


def _get_numeric(val):
    try:
        result = int(val)
    except (ValueError, TypeError):
        result = None
    if result is None:
        try:
            result = float(val)
        except (ValueError, TypeError):
            result = None
    return result


class HrEmployeeTaxSocialBenefitCode(models.Model):
    _name = 'hr.employee.tax_social_benefit.code'
    _description = "Employee's Tax Social Benefit Codes"
    _order = 'code, begin_date'

    code = fields.Char(
        string="Code",
        index=True,
        required=True,
    )

    description = fields.Text(
        string="Description",
        required=True,
    )

    begin_date = fields.Date(
        string="Begin Date",
        required=True,
    )

    end_date = fields.Date(
        string="End Date",
    )

    rate = fields.Float(
        string="Rate",
        digits=PRECISION_TAX_SOCIAL_BENEFIT_RATE,
    )

    _sql_constraints = [
        ('code_uniq', 'UNIQUE (code)', "Code must be unique"),
    ]

    def name_get(self):
        precision = PRECISION_TAX_SOCIAL_BENEFIT_RATE[1]
        if precision > 2:
            precision -= 2
        fmt = '%%s (%%.%df%%%%)' % precision
        return [(rec.id, fmt % (rec.code, rec.rate * 100)) for rec in self]

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = [('code', operator, name)]
            name_numeric = _get_numeric(name)
            if name_numeric is not None:
                name_numeric = '%.3f' % (name_numeric / 100,)
                if operator == 'ilike':
                    name_numeric += '%'
                domain = ['|'] + domain + [('rate', operator, name_numeric)]
        return self._search(expression.AND([domain, args or []]), limit=limit, access_rights_uid=name_get_uid)

    @api.constrains('rate')
    def _check_value(self):
        precision = PRECISION_TAX_SOCIAL_BENEFIT_RATE[1]
        for rec in self:
            if float_compare(rec.rate or 0.0, 0.0, precision_digits=precision) <= 0:
                raise ValidationError(_("The tax social benefit value must be greater than zero"))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('code'):
            default['code'] = _("%s (copy)", self.code)
        return super().copy(default)
