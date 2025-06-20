from odoo import models


OUTSIDE_SCHEDULE_ACCEPTABLE_CODES = [
    'LEAVE110',         # Sick Leaves
    'LEAVE120',         # Vacations
    'LEAVE_UA16',       # Maternity leaves
    'LEAVE_UA09',       # Additional leaves
    'LEAVE_UA11',       # Creative leaves
    'LEAVE_UA07',       # Business Trip
]


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _compute_duration(self):
        in_calendar_days = self.filtered(lambda rec: rec.leave_id and rec.leave_id.in_calendar_days)
        super(HrWorkEntry, self - in_calendar_days)._compute_duration()
        calendar = self.env.ref('selferp_l10n_ua_salary.resource_calendar_service_56h')
        for work_entry in in_calendar_days:
            data = work_entry.employee_id._get_work_days_data_batch(
                work_entry.date_start,
                work_entry.date_stop,
                compute_leaves=False,
                calendar=calendar,
            )
            work_entry.duration = data[work_entry.employee_id.id]['hours']

    def _mark_leaves_outside_schedule(self):
        in_calendar_days = self.filtered(
            lambda rec: rec.leave_id and rec.leave_id.in_calendar_days
        )
        return super(HrWorkEntry, self - in_calendar_days)._mark_leaves_outside_schedule()
