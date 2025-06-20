from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResponsiblePersons(TransactionCase):

    def test_responsible_persons(self):
        self.assertFalse(self.env.company.director_id)
        self.assertFalse(self.env.company.get_director_name())
        self.assertFalse(self.env.company.get_director_vat())
        self.assertFalse(self.env.company.chief_accountant_id)
        self.assertFalse(self.env.company.get_chief_accountant_name())
        self.assertFalse(self.env.company.get_chief_accountant_vat())

        director = self.env['res.partner'].create({
            'name': "Test Director",
        })
        self.env.company.director_id = director
        chief_accountant = self.env['res.partner'].create({
            'name': "Test Chief Accountant",
        })
        self.env.company.chief_accountant_id = chief_accountant

        self.assertTrue(self.env.company.director_id)
        self.assertEqual(self.env.company.director_id, director)
        self.assertEqual(self.env.company.get_director_name(), director.name)
        self.assertEqual(self.env.company.get_director_name(), "Test Director")
        self.assertFalse(self.env.company.get_director_vat())
        self.assertTrue(self.env.company.chief_accountant_id)
        self.assertEqual(self.env.company.chief_accountant_id, chief_accountant)
        self.assertEqual(self.env.company.get_chief_accountant_name(), chief_accountant.name)
        self.assertEqual(self.env.company.get_chief_accountant_name(), "Test Chief Accountant")
        self.assertFalse(self.env.company.get_chief_accountant_vat())

        director.vat = '12345'
        chief_accountant.vat = '67890'

        self.assertTrue(self.env.company.director_id)
        self.assertEqual(self.env.company.director_id, director)
        self.assertEqual(self.env.company.get_director_name(), director.name)
        self.assertEqual(self.env.company.get_director_name(), "Test Director")
        self.assertEqual(self.env.company.get_director_vat(), '12345')
        self.assertTrue(self.env.company.chief_accountant_id)
        self.assertEqual(self.env.company.chief_accountant_id, chief_accountant)
        self.assertEqual(self.env.company.get_chief_accountant_name(), chief_accountant.name)
        self.assertEqual(self.env.company.get_chief_accountant_name(), "Test Chief Accountant")
        self.assertEqual(self.env.company.get_chief_accountant_vat(), '67890')

