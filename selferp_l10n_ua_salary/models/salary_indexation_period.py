from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalaryIndexationPeriod(models.Model):
    _name = 'salary.indexation_period'
    _description = "Salary Indexation Period"
    _order = 'company_id, date_from desc'

    date_from = fields.Date(
        string="From Date",
        required=True,
    )

    date_to = fields.Date(
        string="To Date",
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        index=True,
        default=lambda self: self.env.company,
    )

    def name_get(self):
        result = []
        for rec in self:
            date_from = fields.Date.start_of(rec.date_from, 'month').strftime('%d.%m.%Y')
            date_to = fields.Date.end_of(rec.date_to, 'month').strftime('%d.%m.%Y') if rec.date_to else ''
            display_name = date_from
            if date_to:
                display_name += ' - ' + date_to
            result.append((rec.id, display_name))
        return result

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_date_range(self):
        SalaryIndexationPeriods = self.env['salary.indexation_period']
        for period in self:
            if not period.date_to:
                no_date = SalaryIndexationPeriods.search([
                    ('company_id', '=', period.company_id.id),
                    ('id', '!=', period.id),
                    ('date_to', '=', False),
                ])
                if no_date:
                    invalid_names = '\n'.join([rec.display_name for rec in no_date])
                    raise ValidationError(_("Indexation period for %s is overlapped with another period(s):\n%s.") % (period.display_name, invalid_names))
            overlapped = SalaryIndexationPeriods.search([
                ('company_id', '=', period.company_id.id),
                ('id', '!=', period.id),
                '|',
                '&', ('date_from', '>=', period.date_from), ('date_from', '<=', period.date_to),
                '&', ('date_to', '>=', period.date_from), ('date_to', '<=', period.date_to),
            ])
            if overlapped:
                invalid_names = '\n'.join([rec.display_name for rec in overlapped])
                raise ValidationError(_("Indexation period for %s is overlapped with another period(s):\n%s.") % (period.display_name, invalid_names))
