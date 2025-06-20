from datetime import date, datetime

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_salary.tests.test_salary_common import TestSalaryCommon


@tagged('post_install', '-at_install')
class TestSalaryBusinessTrip(TestSalaryCommon):

    def test_case_iv_supplement_to_min_wage(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2023, 1, 1),
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage_type': 'monthly',
            'wage': 5265.0,
            'state': 'open',
        })

        date_from = date(2023, 1, 1)
        date_to = date(2023, 1, 31)
        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_january = self.env['hr.payslip'].create({
            'name': '%s - January 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_january.compute_sheet()
        payslip_january.action_payslip_done()

        date_from = date(2023, 2, 1)
        date_to = date(2023, 2, 28)
        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_february = self.env['hr.payslip'].create({
            'name': '%s - February 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_february.compute_sheet()
        payslip_february.action_payslip_done()

        business_trip = self.env['hr.leave'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'date_from': datetime(2023, 3, 13),
            'date_to': datetime(2023, 3, 16, 23, 59, 59, 999999),
            'holiday_status_id': self.env.ref('selferp_l10n_ua_salary.hr_leave_type_business_trip').id,
            'state': 'draft',
        })
        business_trip.action_confirm()
        business_trip.action_approve()

        date_from = date(2023, 3, 1)
        date_to = date(2023, 3, 31)
        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_march = self.env['hr.payslip'].create({
            'name': '%s - March 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_march.compute_sheet()
        payslip_march.action_payslip_done()

        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 6810.98, "Wrong salary rule value GROSS")

        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'BASIC')
        self.assertEqual(line.total, 4349.35, "Wrong salary rule value BASIC")
        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'BUSINESS_TRIP')
        self.assertEqual(line.total, 1276.20, "Wrong salary rule value BUSINESS_TRIP")
        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'SUPP_MIN_WAGE')
        self.assertEqual(line.total, 1185.43, "Wrong salary rule value SUPP_MIN_WAGE")

        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 1498.42, "Wrong salary ESV")
        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1225.98, "Wrong salary PDFO")
        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -102.16, "Wrong salary MT")

        line = payslip_march.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 5482.84, "Wrong salary NET")

    def test_case_pic2_worked_less_then_month(self):
        contract = self.env['hr.contract'].create({
            'name': '1',
            'employee_id': self.employee.id,
            'date_start': date(2023, 6, 28),
            'structure_type_id': self.salary_structure_regular.type_id.id,
            'wage_type': 'monthly',
            'wage': 11000.0,
            'state': 'open',
        })

        date_from = date(2023, 6, 1)
        date_to = date(2023, 6, 30)
        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_july = self.env['hr.payslip'].create({
            'name': '%s - June 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_july.compute_sheet()
        payslip_july.action_payslip_done()

        business_trip = self.env['hr.leave'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'date_from': datetime(2023, 7, 4),
            'date_to': datetime(2023, 7, 7, 23, 59, 59, 999999),
            'holiday_status_id': self.env.ref('selferp_l10n_ua_salary.hr_leave_type_business_trip').id,
            'state': 'draft',
        })
        business_trip.action_confirm()
        business_trip.action_approve()

        date_from = date(2023, 7, 1)
        date_to = date(2023, 7, 31)
        self.employee.generate_work_entries(date_from, date_to, True)
        payslip_july = self.env['hr.payslip'].create({
            'name': '%s - July 2023' % self.employee.name,
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.salary_structure_regular.id,
            'payment_type': 'salary',
        })
        payslip_july.compute_sheet()
        payslip_july.action_payslip_done()

        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'GROSS')
        self.assertEqual(line.total, 11000.0, "Wrong salary rule value GROSS")

        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'BASIC')
        self.assertEqual(line.total, 8904.76, "Wrong salary rule value BASIC")
        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'BUSINESS_TRIP')
        self.assertEqual(line.total, 2095.24, "Wrong salary rule value BUSINESS_TRIP")

        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'ESV')
        self.assertEqual(line.total, 2420.0, "Wrong salary ESV")
        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'PDFO')
        self.assertEqual(line.total, -1980.0, "Wrong salary PDFO")
        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'MT')
        self.assertEqual(line.total, -165.0, "Wrong salary MT")

        line = payslip_july.line_ids.filtered(lambda ps: ps.salary_rule_id.code == 'NET')
        self.assertEqual(line.total, 8855.0, "Wrong salary NET")
