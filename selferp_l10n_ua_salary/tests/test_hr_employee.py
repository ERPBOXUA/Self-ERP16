import datetime

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged, Form


@tagged('post_install', '-at_install')
class TestHrEmployee(TransactionCase):

    def test_social_tax_benefit(self):
        form = Form(self.env['hr.employee'])
        form.last_name = "New worker"

        tax_social_benefit_code = self.env.ref('selferp_l10n_ua_salary.hr_employee_tax_social_benefit_code_4')

        try:
            with form.tax_social_benefit_ids.new() as tsb:
                tsb.date_to = datetime.date(2023, 12, 31)
                tsb.value = 100
            form.save()
            self.fail("Missing from date")
        except AssertionError:
            if form.tax_social_benefit_ids:
                form.tax_social_benefit_ids.remove(0)

        try:
            with form.tax_social_benefit_ids.new() as tsb:
                tsb.date_from = datetime.date(2023, 1, 1)
                tsb.tax_social_benefit_code_id = tax_social_benefit_code
            self.save()
            self.fail("Missing to date")
        except AssertionError:
            if form.tax_social_benefit_ids:
                form.tax_social_benefit_ids.remove(0)

        try:
            with form.tax_social_benefit_ids.new() as tsb:
                tsb.date_from = datetime.date(2023, 1, 1)
                tsb.date_to = datetime.date(2023, 12, 31)
            form.save()
            self.fail("Missing percents value")
        except AssertionError:
            if form.tax_social_benefit_ids:
                form.tax_social_benefit_ids.remove(0)

        try:
            with form.tax_social_benefit_ids.new() as tsb:
                tsb.date_from = datetime.date(2023, 1, 1)
                tsb.date_to = datetime.date(2023, 1, 1)
                tsb.value = 100
            form.save()
            self.fail("Invalid date range")
        except AssertionError:
            if form.tax_social_benefit_ids:
                form.tax_social_benefit_ids.remove(0)

        with form.tax_social_benefit_ids.new() as tsb:
            tsb.date_from = datetime.date(2023, 1, 1)
            tsb.date_to = datetime.date(2023, 12, 31)
            tsb.tax_social_benefit_code_id = tax_social_benefit_code
        form.save()

    def test_disability_group(self):
        disability_group = self.env.ref('selferp_l10n_ua_salary.hr_salary_disability_group_1')

        form = Form(self.env['hr.employee'])
        form.last_name = "New worker"

        try:
            with form.disability_group_ids.new() as dg:
                dg.apply_date = datetime.date(2023, 1, 1)
            form.save()
            self.fail("Missing disability group")
        except AssertionError:
            if form.disability_group_ids:
                form.disability_group_ids.remove(0)

        try:
            with form.disability_group_ids.new() as dg:
                dg.disability_group_id = disability_group
            form.save()
            self.fail("Missing date")
        except AssertionError:
            if form.disability_group_ids:
                form.disability_group_ids.remove(0)

        with form.disability_group_ids.new() as dg:
            dg.apply_date = datetime.date(2023, 1, 1)
            dg.disability_group_id = disability_group
        form.save()

    def test_sick_leave_rate(self):
        sick_leave_rate = self.env['hr.salary.sick_leave.rate'].create({
            'name': 'Work experience of more than a year',
            'rate': 100,
        })

        form = Form(self.env['hr.employee'])
        form.last_name = "New worker"

        try:
            with form.sick_leave_rate_ids.new() as slr:
                slr.apply_date = datetime.date(2023, 1, 1)
            form.save()
            self.fail("Missing sick leave rate")
        except AssertionError:
            if form.sick_leave_rate_ids:
                form.sick_leave_rate_ids.remove(0)

        try:
            with form.sick_leave_rate_ids.new() as slr:
                slr.sick_leave_rate_id = sick_leave_rate
            form.save()
            self.fail("Missing date")
        except AssertionError:
            if form.sick_leave_rate_ids:
                form.sick_leave_rate_ids.remove(0)

        with form.sick_leave_rate_ids.new() as slr:
            slr.apply_date = datetime.date(2023, 1, 1)
            slr.sick_leave_rate_id = sick_leave_rate
        form.save()

    def test_name_firstname_lastname_patronymic(self):
        create_employee_only_firstname = self.env['hr.employee'].create({
            'name': "First_name",
        })
        self.assertEqual(create_employee_only_firstname.last_name, False)
        self.assertEqual(create_employee_only_firstname.first_name, "First_name")
        self.assertEqual(create_employee_only_firstname.patronymic, False)

        create_employee_firstname_lastname = self.env['hr.employee'].create({
            'name': "Last_name First_name",
        })
        self.assertEqual(create_employee_firstname_lastname.last_name, "Last_name")
        self.assertEqual(create_employee_firstname_lastname.first_name, "First_name")
        self.assertEqual(create_employee_firstname_lastname.patronymic, False)

        create_employee_full = self.env['hr.employee'].create({
            'name': "Last_name First_name Patronymic",
        })
        self.assertEqual(create_employee_full.last_name, "Last_name")
        self.assertEqual(create_employee_full.first_name, "First_name")
        self.assertEqual(create_employee_full.patronymic, "Patronymic")

        form = Form(create_employee_full)

        form.first_name = "First_name_changed"
        self.assertEqual(form.name, "Last_name First_name_changed Patronymic")

        form.patronymic = "Patronymic_changed"
        self.assertEqual(form.name, "Last_name First_name_changed Patronymic_changed")

        form.last_name = ""
        self.assertEqual(form.name, "First_name_changed Patronymic_changed")

        form.save()
        self.assertEqual(create_employee_full.name, "First_name_changed Patronymic_changed")
