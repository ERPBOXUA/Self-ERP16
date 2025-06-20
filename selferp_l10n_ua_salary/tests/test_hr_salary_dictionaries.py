import datetime

from psycopg2.errors import CheckViolation
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import Form
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestHrSalaryDictionaries(TransactionCase):

    def test_create_hr_salary_cost_of_living(self):
        form = Form(self.env['hr.salary.cost_of_living'])
        try:
            with self.cr.savepoint():
                form.save()
                self.fail("Required fields check filed")
        except AssertionError:
            pass

        form.date = datetime.date(2023, 1, 1)
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Empty value check filed")
        except CheckViolation:
            pass

        self.assertEqual(form.value, 0, "Initial value must be 0")

        form.value = -2684.0
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Negative value check filed")
        except CheckViolation:
            pass

        form.value = 2684.0
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Rest of constrains are failed")
        except CheckViolation:
            pass

        form.value = 2684.0
        form.value_children_from_6_to_18 = 2833.0
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Rest of constrains are failed")
        except CheckViolation:
            pass

        form.value = 2684.0
        form.value_children_from_6_to_18 = 2833.0
        form.value_children_under_6 = 2272.0
        form.save()

    def test_create_hr_salary_disability_group(self):
        form = Form(self.env['hr.salary.disability_group'])
        try:
            form.save()
            self.fail("Required fields check filed")
        except AssertionError:
            pass

        form.name = '1st'
        form.code = '1'
        form.save()

    def test_copy_hr_salary_disability_group(self):
        group1 = self.env['hr.salary.disability_group'].create({
            'name': '1st',
            'code': '1',
        })
        group2 = group1.copy()
        self.assertNotEqual(group1.name, group2.name)
        self.assertNotEqual(group1.code, group2.code)

    def test_create_hr_salary_inflation_index(self):
        form = Form(self.env['hr.salary.inflation_index'])
        try:
            with self.cr.savepoint():
                form.save()
                self.fail("Required fields check filed")
        except AssertionError:
            pass

        form.date = datetime.date(2023, 4, 1)
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Empty value check filed")
        except CheckViolation:
            pass

        self.assertEqual(form.value, 0, "Initial value must be 0")

        form.value = -100.2
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Negative value check filed")
        except CheckViolation:
            pass

        form.value = 100.2
        form.save()

    def test_create_hr_salary_minimum_wage(self):
        form = Form(self.env['hr.salary.minimum_wage'])
        try:
            with self.cr.savepoint():
                form.save()
                self.fail("Required fields check filed")
        except AssertionError:
            pass

        form.date = datetime.date(2023, 1, 1)
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Empty values check filed")
        except CheckViolation:
            pass

        self.assertEqual(form.value_monthly, 0, "Initial monthly value must be 0")
        self.assertEqual(form.value_hourly, 0, "Initial hourly value must be 0")

        form.value_monthly = 6700
        form.value_hourly = -40.46
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Negative value check filed")
        except CheckViolation:
            pass

        form.value_monthly = -6700
        form.value_hourly = 40.46
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Negative value check filed")
        except CheckViolation:
            pass

        form.value_monthly = 6700
        form.value_hourly = 40.46
        form.save()

    def test_create_hr_salary_sick_leave_rate(self):
        form = Form(self.env['hr.salary.sick_leave.rate'])
        try:
            with self.cr.savepoint():
                form.save()
                self.fail("Required fields check filed")
        except AssertionError:
            pass

        form.name = "More then one year"
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Empty values check filed")
        except CheckViolation:
            pass

        self.assertEqual(form.rate, 0, "Initial rate must be 0")

        form.rate = -100
        try:
            with self.cr.savepoint():
                with mute_logger('odoo.sql_db'):
                    form.save()
                self.fail("Negative value check filed")
        except CheckViolation:
            pass

        form.rate = 100
        form.save()

    def test_copy_hr_salary_sick_leave_rate(self):
        rate1 = self.env['hr.salary.sick_leave.rate'].create({
            'name': "More then one year",
            'rate': 100,
        })
        rate2 = rate1.copy()
        self.assertNotEqual(rate1.name, rate2.name)
        self.assertEqual(rate1.rate, rate2.rate)
