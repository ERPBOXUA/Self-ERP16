from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployeeTaxSocialBenefit(models.Model):
    _name = 'hr.employee.tax_social_benefit'
    _description = "Employee Tax Social Benefits"
    _order = 'employee_id, date_from desc, date_to desc'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        required=True,
        index=True,
        ondelete='cascade',
    )

    date_from = fields.Date(
        string="From Date",
        required=True,
    )

    date_to = fields.Date(
        string="To Date",
        required=True,
    )

    tax_social_benefit_code_id = fields.Many2one(
        comodel_name='hr.employee.tax_social_benefit.code',
        string="Code",
        required=True,
    )

    on_children = fields.Boolean(
        string="On Children",
    )

    children_qty = fields.Integer(
        string="Children Qty",
    )

    value = fields.Float(
        string="Percents",
        related='tax_social_benefit_code_id.rate',
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if not (rec.date_from and rec.date_to):
                raise ValidationError(_("The tax social benefit date range must be set"))
            if not (rec.date_from < rec.date_to):
                raise ValidationError(_("The tax social benefit start date must be before end date"))

    @api.constrains('on_children')
    def _check_children_qty(self):
        for rec in self.filtered(lambda benefit: benefit.on_children):
            if not rec.children_qty or rec.children_qty <= 0:
                raise ValidationError(_("The children quantity of the tax social benefit record is missing"))

    @api.constrains('on_children', 'tax_social_benefit_code_id')
    def _check_tax_social_benefit_code_id(self):
        for rec in self.filtered(lambda benefit: benefit.on_children):
            if rec.tax_social_benefit_code_id.code not in ('02', '04'):
                raise ValidationError(_("The code of the tax social benefit on children must be '02' or '04'"))
