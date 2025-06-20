from odoo import models, fields


class HrEmployeeIncomeFeatureCode(models.Model):
    _name = 'hr.employee.income_feature_code'
    _description = "Income Feature Codes"
    _order = 'code, begin_date'

    code = fields.Char(
        string="Code",
        required=True,
    )

    description = fields.Text(
        string="Description",
        required=True,
    )

    short_description = fields.Char(
        string="Short Description",
        required=True,
    )

    begin_date = fields.Date(
        string="Begin Date",
        required=True,
    )

    end_date = fields.Date(
        string="End Date",
    )

    def name_get(self):
        return [(rec.id, '%s, %s' % (rec.code, rec.short_description)) for rec in self]
