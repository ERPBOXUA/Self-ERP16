from datetime import date, datetime

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_salary.tests.test_salary_common import TestSalaryCommon


@tagged('post_install', '-at_install')
class TestSalary(TestSalaryCommon):

    def test_case_1_common(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2023, 1, 1),
            'wage_type': 'monthly',
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage': 10000.0,
            'state': 'open',
        })

        date_from = date(2023, 8, 1)
        date_to = date(2023, 8, 31)

        self.employee.generate_work_entries(date_from, date_to, True)

        payslip_advance = self.env['hr.payslip'].create({
            'name': '%s Advance - August 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'advance_salary',
            'salary_advance_calculation': 'percentage',
            'salary_advance_percents': 0.5,
        })
        payslip_advance.compute_sheet()
        payslip_advance.action_payslip_done()

        line = payslip_advance.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_GROSS')
        self.assertEqual(line.total, 5000.0, "Wrong advance salary GROSS")

        line = payslip_advance.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_ESV')
        self.assertEqual(line.total, 1100.0, "Wrong advance salary ESV")

        line = payslip_advance.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_PDFO')
        self.assertEqual(line.total, -900.0, "Wrong advance salary PDFO")

        line = payslip_advance.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_MT')
        self.assertEqual(line.total, -75.0, "Wrong advance salary MT")

        line = payslip_advance.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_NET')
        self.assertEqual(line.total, 4025.0, "Wrong advance salary GROSS")

        payslip_salary = self.env['hr.payslip'].create({
            'name': '%s - August 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_salary.compute_sheet()

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_PAID')
        self.assertEqual(line.total, -4025.0, "Wrong advance salary ADV_PAID")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_ESV_PAID')
        self.assertEqual(line.total, 1100.0, "Wrong advance salary ADV_ESV_PAID")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_PDFO_PAID')
        self.assertEqual(line.total, -900.0, "Wrong advance salary ADV_PDFO_PAID")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ADV_MT_PAID')
        self.assertEqual(line.total, -75.0, "Wrong advance salary ADV_MT_PAID")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 10000.0, "Wrong salary GROSS")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 2200.0, "Wrong salary ESV")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1800.0, "Wrong salary PDFO")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -150.0, "Wrong salary MT")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV_FINAL')
        self.assertEqual(line.total, 1100.0, "Wrong salary ESV_FINAL")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO_FINAL')
        self.assertEqual(line.total, -900.0, "Wrong salary PDFO_FINAL")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT_FINAL')
        self.assertEqual(line.total, -75.0, "Wrong salary MT_FINAL")

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 4025.0, "Wrong salary NET")

    def test_case_2_supplement_to_min_wage(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2022, 1, 1),
            'wage_type': 'monthly',
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage': 5500.0,
            'state': 'open',
        })

        date_from = date(2022, 3, 1)
        date_to = date(2022, 3, 31)

        self.employee.generate_work_entries(date_from, date_to, True)

        payslip_salary = self.env['hr.payslip'].create({
            'name': '%s - March 2022' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_salary.compute_sheet()

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 6500.0, "Wrong salary GROSS")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 1430.0, "Wrong salary ESV")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1170.0, "Wrong salary PDFO")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -97.50, "Wrong salary MT")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 5232.5, "Wrong salary NET")

    def test_case_3_esv_limits(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2021, 1, 1),
            'wage_type': 'monthly',
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage': 100000.0,
            'state': 'open',
        })

        date_from = date(2021, 1, 1)
        date_to = date(2021, 1, 31)

        self.employee.generate_work_entries(date_from, date_to, True)

        payslip_salary = self.env['hr.payslip'].create({
            'name': '%s - January 2021' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_salary.compute_sheet()

        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 100000.0, "Wrong salary GROSS")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 19800.0, "Wrong salary ESV")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -18000.0, "Wrong salary PDFO")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -1500.0, "Wrong salary MT")
        line = payslip_salary.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 80500.0, "Wrong salary NET")
