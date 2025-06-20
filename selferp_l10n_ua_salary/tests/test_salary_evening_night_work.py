from datetime import date, datetime, time

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_salary.tests.test_salary_common import TestSalaryCommon


@tagged('post_install', '-at_install')
class TestSalaryBusinessTrip(TestSalaryCommon):

    def test_case_evening_work_base(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2023, 1, 1),
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage_type': 'monthly',
            'wage': 18000.0,
            'state': 'open',
        })

        work_type_evening = self.env.ref('selferp_l10n_ua_salary.hr_work_entry_type_work_in_the_evening')
        work_type_evening.overtime = True
        work_type_evening.surcharge_percents = 0.35

        work_evening = [
            date(2023, 4, 3),
            date(2023, 4, 4),
            date(2023, 4, 5),
            date(2023, 4, 6),
            date(2023, 4, 7),
            date(2023, 4, 10),
            date(2023, 4, 11),
            date(2023, 4, 12),
            date(2023, 4, 13),
            date(2023, 4, 14),
            date(2023, 4, 17),
        ]
        HrWorkEntry = self.env['hr.work.entry']
        for evening_date in work_evening:
            start = datetime.combine(evening_date, time(17, 0))
            end = datetime.combine(evening_date, time(21, 0))
            HrWorkEntry.create({
                'name': "Work In The Evening: %s" % self.employee.name,
                'employee_id': self.employee.id,
                'work_entry_type_id': work_type_evening.id,
                'date_start': start,
                'date_stop': end,
            })

        leave_start = datetime(2023, 4, 25, 13, 0, 0)
        leave_end = datetime(2023, 4, 30, 17, 0, 0)
        leave = self.env['hr.leave'].create({
            'name': "%s's Leave" % self.employee.name,
            'holiday_type': 'employee',
            'payslip_state': 'done',
            'holiday_status_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
            'employee_id': self.employee.id,
            'date_from': leave_start,
            'date_to': leave_end,
            'request_date_from': leave_start,
            'request_date_to': leave_end,
        })
        leave._compute_date_from_to()
        leave.action_approve()

        date_from = date(2023, 4, 1)
        date_to = date(2023, 4, 30)
        self.employee.generate_work_entries(date_from, date_to, True)

        payslip_april = self.env['hr.payslip'].create({
            'name': '%s - April 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_april.compute_sheet()

        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'WORK_EVENING')
        self.assertEqual(line.total, 6682.50, "Wrong salary rule value WORK_EVENING")

        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'BASIC')
        self.assertEqual(line.total, 14400.0, "Wrong salary rule value BASIC")

        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 21082.5, "Wrong salary rule value GROSS")

        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 4638.15, "Wrong salary ESV")
        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -3794.85, "Wrong salary PDFO")
        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -316.24, "Wrong salary MT")

        line = payslip_april.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 16971.41, "Wrong salary NET")
