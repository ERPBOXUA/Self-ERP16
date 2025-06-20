from odoo import models, fields


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    in_calendar_days = fields.Boolean(
        string="In Calendar Days",
        default=False,
    )

    def _get_leaves_domain(self, states):
        now = fields.Datetime.now()
        min_datetime = fields.Datetime.start_of(now, 'year')
        max_datetime = fields.Datetime.end_of(now, 'year')
        return [
            ('holiday_status_id', 'in', self.ids),
            ('date_from', '>=', min_datetime),
            ('date_from', '<=', max_datetime),
            ('state', 'in', states),
            ('employee_id.company_id', 'in', self.env.companies.ids + [False]),
        ]

    def _compute_allocation_count(self):
        domain = self._get_leaves_domain(('confirm', 'validate'))
        grouped_res = self.env['hr.leave.allocation']._read_group(domain, ['holiday_status_id'], ['holiday_status_id'])
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.allocation_count = grouped_dict.get(allocation.id, 0)

    def _compute_group_days_leave(self):
        domain = self._get_leaves_domain(('validate', 'validate1', 'confirm'))
        grouped_res = self.env['hr.leave']._read_group(domain, ['holiday_status_id'], ['holiday_status_id'])
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_leave = grouped_dict.get(allocation.id, 0)

    def action_see_days_allocated(self):
        action = super().action_see_days_allocated()
        if action:
            domain = action.get('domain') or []
            domain = [('employee_id.company_id', 'in', self.env.companies.ids + [False])] + domain
            action['domain'] = domain
        return action

    def action_see_group_leaves(self):
        action = super().action_see_group_leaves()
        if action:
            domain = action.get('domain') or []
            domain = [('employee_id.company_id', 'in', self.env.companies.ids + [False])] + domain
            action['domain'] = domain
        return action
