from datetime import date, datetime, time

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_salary.tests.test_salary_common import TestSalaryCommon


@tagged('post_install', '-at_install')
class TestSalaryAdvance(TestSalaryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.env['hr.contract'].create({
            'name': '1',
            'employee_id': cls.employee.id,
            'date_start': date(2023, 1, 1),
            'wage': 6700.0,
            'state': 'open',
        })

    def test_case_1_first15d_full_time(self):
        self.contract._generate_work_entries(
            datetime.combine(date(2023, 2, 1), time.min),
            datetime.combine(date(2023, 2, 28), time.max),
            True,
        )
        payslip = self.env['hr.payslip'].create({
            'name': '%s - February 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'advance_salary',
            'salary_advance_calculation':  'first_15_days',
        })
        payslip.compute_sheet()
        advance_line_gross = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_GROSS')
        self.assertEqual(advance_line_gross.total, 3685.0, "Wrong advance salary GROSS")
        advance_line_net = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_NET')
        self.assertEqual(advance_line_net.total, 2966.42, "Wrong advance salary NET")

    def test_case_2_percents_full_time(self):
        self.contract._generate_work_entries(
            datetime.combine(date(2023, 2, 1), time.min),
            datetime.combine(date(2023, 2, 28), time.max),
            True,
        )
        payslip = self.env['hr.payslip'].create({
            'name': '%s - February 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'advance_salary',
            'salary_advance_calculation': 'percentage',
            'salary_advance_percents': 0.5,
        })
        payslip.compute_sheet()
        advance_line_gross = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_GROSS')
        self.assertEqual(advance_line_gross.total, 3350.0, "Wrong advance salary GROSS")
        advance_line_net = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_NET')
        self.assertEqual(advance_line_net.total, 2696.75, "Wrong advance salary NET")

    def test_case_3_first15d_with_leaves(self):
        self._create_leave(date(2023, 2, 6), datetime(2023, 2, 10), self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id)

        self.contract._generate_work_entries(
            datetime.combine(date(2023, 2, 1), time.min),
            datetime.combine(date(2023, 2, 28), time.max),
            True,
        )
        payslip = self.env['hr.payslip'].create({
            'name': '%s - February 2023 (with leaves)' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'advance_salary',
            'salary_advance_calculation': 'first_15_days',
        })
        payslip.compute_sheet()
        advance_line_gross = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_GROSS')
        self.assertEqual(advance_line_gross.total, 2010.0, "Wrong advance salary GROSS")
        advance_line_net = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_NET')
        self.assertEqual(advance_line_net.total, 1618.05, "Wrong advance salary NET")

    def test_case_4_percents_with_leaves(self):
        self._create_leave(date(2023, 2, 6), datetime(2023, 2, 10), self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id)

        self.contract._generate_work_entries(
            datetime.combine(date(2023, 2, 1), time.min),
            datetime.combine(date(2023, 2, 28), time.max),
            True,
        )
        payslip = self.env['hr.payslip'].create({
            'name': '%s - February 2023 (with leaves)' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date(2023, 2, 1),
            'date_to': date(2023, 2, 28),
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'advance_salary',
            'salary_advance_calculation': 'percentage',
            'salary_advance_percents': 0.5,
        })
        payslip.compute_sheet()
        advance_line_gross = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_GROSS')
        self.assertEqual(advance_line_gross.total, 1827.27, "Wrong advance salary GROSS")
        advance_line_net = payslip.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_NET')
        self.assertEqual(advance_line_net.total, 1470.95, "Wrong advance salary NET")

    def _create_leave(self, leave_start, leave_end, leave_type_id):
        leave_start = datetime(leave_start.year, leave_start.month, leave_start.day, 0, 0, 0)
        leave_end = datetime(leave_end.year, leave_end.month, leave_end.day, 23, 59, 59)
        leave = self.env['hr.leave'].create({
            'name': "%s's Leave" % self.employee.name,
            'holiday_type': 'employee',
            'payslip_state': 'done',
            'holiday_status_id': leave_type_id,
            'employee_id': self.employee.id,
            'date_from': leave_start,
            'date_to': leave_end,
            'request_date_from': leave_start,
            'request_date_to': leave_end,
        })
        leave._compute_date_from_to()
        leave.action_approve()
        return leave
