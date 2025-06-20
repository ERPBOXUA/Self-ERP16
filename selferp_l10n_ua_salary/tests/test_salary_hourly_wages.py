from datetime import date

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_salary.tests.test_salary_common import TestSalaryCommon


@tagged('post_install', '-at_install')
class TestSalaryHourlyWages(TestSalaryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.env['hr.contract'].create({
            'name': '1',
            'employee_id': cls.employee.id,
            'date_start': date(2023, 1, 1),
            'structure_type_id': cls.salary_structure_hourly.type_id.id,
            'wage_type': 'hourly',
            'hourly_wage': 40.46,
            'wage': 0.0,
            'state': 'open',
        })

    def test_case_1_common(self):
        date_from = date(2023, 1, 1)
        date_to = date(2023, 1, 31)

        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_salary = self.env['hr.payslip'].create({
            'name': '%s - January 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_hourly.id,
            'payment_type': 'salary',
        })
        payslip_salary.compute_sheet()

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 7120.96, "Wrong salary GROSS")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 1566.61, "Wrong salary ESV")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1281.77, "Wrong salary PDFO")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -106.81, "Wrong salary MT")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 5732.38, "Wrong salary NET")

    def test_case_2_salary_less_then_minimal(self):
        date_from = date(2023, 2, 1)
        date_to = date(2023, 2, 28)

        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_salary = self.env['hr.payslip'].create({
            'name': '%s - February 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_hourly.id,
            'payment_type': 'salary',
        })
        payslip_salary.compute_sheet()

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 6473.60, "Wrong salary GROSS")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 1474.0, "Wrong salary ESV")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1165.25, "Wrong salary PDFO")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -97.10, "Wrong salary MT")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 5211.25, "Wrong salary NET")
