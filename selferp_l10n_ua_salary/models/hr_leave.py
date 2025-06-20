from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    in_calendar_days = fields.Boolean(
        related='holiday_status_id.in_calendar_days',
        store=True,
        readonly=True,
    )

    @api.depends('date_from', 'date_to', 'employee_id', 'holiday_status_id', 'holiday_status_id.in_calendar_days')
    def _compute_number_of_days(self):
        in_calendar_days = self.filtered(lambda rec: rec.holiday_status_id.in_calendar_days)
        super(HrLeave, self - in_calendar_days)._compute_number_of_days()
        calendar = self.env.ref('selferp_l10n_ua_salary.resource_calendar_service_56h')
        hours_per_day = calendar.hours_per_day
        if not hours_per_day or float_is_zero(hours_per_day, precision_digits=2):
            hours_per_day = 8.0
        for holiday in in_calendar_days:
            if holiday.date_from and holiday.date_to:
                hours = calendar.get_work_hours_count(holiday.date_from, holiday.date_to)
                holiday.number_of_days = float_round(hours / hours_per_day, precision_digits=2)
            else:
                holiday.number_of_days = 0

    def action_refuse(self):
        return super(HrLeave, self.with_context(check_work_entries=False, **self.env.context)).action_refuse()

    def action_approve(self):
        return super(HrLeave, self.with_context(check_work_entries=False, **self.env.context)).action_approve()
