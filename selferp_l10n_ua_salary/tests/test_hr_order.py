from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHrOrder(TransactionCase):

    def test_create_hr_order(self):
        hr_order_type_recruitment = self.env.ref('selferp_l10n_ua_salary.hr_order_type_recruitment')

        hr_order_1 = self.env['hr.order'].create({
            'name': 'hr_1',
            'type_id': hr_order_type_recruitment.id,
            'employee_id': self.env.ref('base.user_demo').id,
            'order_date': fields.Date.today(),
        })
        self.assertEqual(hr_order_1.name, 'hr_1')
        try:
            hr_order_2 = self.env['hr.order'].create({
                'name': 'hr_1',
                'type_id': hr_order_type_recruitment.id,
                'employee_id': self.env.ref('base.user_demo').id,
                'order_date': fields.Date.today(),
            })
            self.fail("Order block is already exist with this Order Name")
        except UserError:
            pass
