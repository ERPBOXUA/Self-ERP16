from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from .common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestFirstEventCredit(VATTestCommon):

    def test_vat_first_event_credit_case1(self):
        date_01 = datetime.strptime('2023-05-04', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': 'My partner',
            'tracking_first_event': 'in_general',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 0,
            'standard_price': 1000.0,
            'taxes_id': [Command.link(self.tax_sale_20_exclude.id)],
        })

        po_1 = self.create_purchase_order(
            partner=partner,
            products=[product],
            counts=[10],
            prices=[1000],
            date=date_01,
        )

        pay_line = self.create_contract_bank_statement_line(
            partner=partner,
            amount=-5999.99,
            date=date_01,
            purchase_order=po_1,
        )

        pay = self.validate_statement_line(pay_line)

        self.check_first_event(pay, 5999.99, "First payment")

    def test_vat_first_event_credit_case2(self):
        date_01 = datetime.strptime('2023-05-03', '%Y-%m-%d').date()

        date_02 = datetime.strptime('2023-05-04', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': 'My partner',
            'tracking_first_event': 'in_general',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 0,
            'standard_price': 1000.0,
            'taxes_id': [Command.link(self.tax_sale_20_exclude.id)],
        })

        po_1 = self.create_purchase_order(
            partner=partner,
            products=[product],
            counts=[10],
            prices=[1000],
            date=date_01,
        )

        self.confirm_purchase_order(po_1)
        self.receive_purchase_order(po_1, qtys=[5])

        bill_1 = self.invoicing_purchase_order(po_1)
        self.post_invoice(bill_1, invoice_date=date_01)

        pay_line = self.create_contract_bank_statement_line(
            partner=partner,
            amount=-12000,
            date=date_02,
            purchase_order=po_1,
        )

        pay = self.validate_statement_line(pay_line)

        self.check_first_event(bill_1, 6000, "Receive")
        self.check_first_event(pay, 6000, "Payment")

