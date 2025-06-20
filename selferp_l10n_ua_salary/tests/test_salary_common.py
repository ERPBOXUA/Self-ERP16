from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSalaryCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('hr_work_entry.work_entry_type_attendance').timesheet_ccode = 'Р'
        cls.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').timesheet_ccode = 'НА'
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Smith',
            'employment_type': 'employment_main_place',
        })
        cls.salary_structure_regular = cls.env.ref('selferp_l10n_ua_salary.hr_payroll_structure_ua_salary_employee')
        cls.salary_structure_hourly = cls.env.ref('selferp_l10n_ua_salary.hr_payroll_structure_ua_hourly_wages')
        cls.env['hr.salary.minimum_wage'].create([
            {
                'date': date(2021, 1, 1),
                'value_monthly': 6000.0,
                'value_hourly': 36.11,
            },
            {
                'date': date(2021, 12, 1),
                'value_monthly': 6500.0,
                'value_hourly': 39.12,
            },
            {
                'date': date(2022, 1, 1),
                'value_monthly': 6500.0,
                'value_hourly': 39.26,
            },
            {
                'date': date(2022, 10, 1),
                'value_monthly': 6700.0,
                'value_hourly': 40.46,
            },
        ])
