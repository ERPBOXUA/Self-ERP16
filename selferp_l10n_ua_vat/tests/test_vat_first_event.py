from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from .common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestFirstEvent(VATTestCommon):

    def test_vat_first_event_case1(self):
        date_01 = datetime.strptime('2023-03-01', '%Y-%m-%d').date()
        date_02 = datetime.strptime('2023-03-02', '%Y-%m-%d').date()
        date_03 = datetime.strptime('2023-03-03', '%Y-%m-%d').date()
        date_04 = datetime.strptime('2023-03-04', '%Y-%m-%d').date()
        date_06 = datetime.strptime('2023-03-06', '%Y-%m-%d').date()
        date_09 = datetime.strptime('2023-03-09', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': 'My partner',
            'tracking_first_event': 'in_general',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 0,
            'standard_price': 1000.0,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        pay_1_line = self.create_bank_statement_line(
            partner=partner,
            amount=10000,
            date=date_01,
        )
        pay_1 = self.validate_statement_line(pay_1_line)

        pay_2_line = self.create_bank_statement_line(
            partner=partner,
            amount=15000,
            date=date_02,
        )
        pay_2 = self.validate_statement_line(pay_2_line)

        invoice_1 = self.create_invoice(
            partner=partner,
            products=[product],
            amounts=[30000],
            taxes=[],
            date=date_03,
        )
        self.post_invoice(invoice_1)

        invoice_2 = self.create_invoice(
            partner=partner,
            products=[product],
            amounts=[45000],
            date=date_04,
        )
        self.post_invoice(invoice_2)

        pay_3_line = self.create_bank_statement_line(
            partner=partner,
            amount=40000,
            date=date_06,
        )
        pay_3 = self.validate_statement_line(pay_3_line)

        # TODO: check it - originally this case uses invoice here
        pay_4_line = self.create_bank_statement_line(
            partner=partner,
            amount=30000,
            date=date_09,
        )
        pay_4 = self.validate_statement_line(pay_4_line)

        op_list = [pay_1.id, pay_2.id, pay_3.id,  pay_4.id, invoice_1.id, invoice_2.id]

        event_data = self.env['account.vat.calculations']._calc_first_event([('move_id', 'in', op_list)])

        self.check_first_events_data(event_data, pay_1, 10000, 'First payment')
        self.check_first_events_data(event_data, pay_2, 15000, 'Second payment')
        self.check_first_events_data(event_data, invoice_1, 5000, 'First invoice')
        self.check_first_events_data(event_data, invoice_2, 45000, 'Second invoice')
        self.check_first_events_data(event_data, pay_3, 0, 'Third payment')
        self.check_first_events_data(event_data, pay_4, 20000, 'Forth payment')

    def test_vat_first_event_case2(self):
        date_01 = datetime.strptime('2023-03-01', '%Y-%m-%d').date()
        date_02 = datetime.strptime('2023-03-02', '%Y-%m-%d').date()
        date_03 = datetime.strptime('2023-03-03', '%Y-%m-%d').date()
        date_04 = datetime.strptime('2023-03-04', '%Y-%m-%d').date()
        date_15 = datetime.strptime('2023-03-15', '%Y-%m-%d').date()
        date_30 = datetime.strptime('2023-03-30', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Бджола"',
            'tracking_first_event': 'in_general',
        })

        product_10 = self.env['product.product'].create({
            'name': 'product 10',
            'uom_id': self.uom_unit_id,
            'lst_price': 3000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })
        product_11 = self.env['product.product'].create({
            'name': 'product 11',
            'uom_id': self.uom_unit_id,
            'lst_price': 2000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order1 = self.create_sale_order(
            partner,
            [product_10, product_11],
            [10, 5],
            [3000.0, 2000.0],
            date_order=date_01,
        )
        self.confirm_sale_order(sale_order1, date_order=date_01)

        invoice1 = self.create_invoice(partner, [product_10], [15000], date=date_02, sale_order=sale_order1)
        self.post_invoice(invoice1, invoice_date=date_02)

        sale_order2 = self.create_sale_order(
            partner,
            [product_11],
            [10],
            [2000.0],
            date_order=date_02,
        )
        self.confirm_sale_order(sale_order2, date_order=date_02)

        pay_line1 = self.create_contract_bank_statement_line(partner, 20000, date=date_03, sale_order=sale_order1)
        pay1 = self.validate_statement_line(pay_line1)

        invoice2 = self.create_invoice(partner, [product_10, product_11], [15000, 10000], date=date_04, sale_order=sale_order1)
        self.post_invoice(invoice2, invoice_date=date_04)

        docs = self.generate_vat_documents_by_partner(partner, date_01, date_15)

        self.assertEqual(len(docs), 3, "Must be three documents")

        invoice3 = self.invoicing_sale_order(sale_order2, date=date_30)
        self.post_invoice(invoice3, invoice_date=date_30)

        docs = self.generate_vat_documents_by_partner(partner, date_15, date_30)
        self.assertEqual(len(docs), 1, "Must be three documents")

    def test_vat_first_event_902_wrong_order(self):
        date_01 = datetime.strptime('2023-03-01', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Бджола"',
            'tracking_first_event': 'in_general',
        })

        product_10 = self.env['product.product'].create({
            'name': 'product 10',
            'uom_id': self.uom_unit_id,
            'lst_price': 3000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })
        product_11 = self.env['product.product'].create({
            'name': 'product 11',
            'uom_id': self.uom_unit_id,
            'lst_price': 2000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order1 = self.create_sale_order(
            partner,
            [product_10],
            [10],
            [3000.0],
            date_order=date_01,
        )
        self.confirm_sale_order(sale_order1, date_order=date_01)

        vat_invoice_1 = self.create_invoice(partner, [product_10], [30000], date=date_01, sale_order=sale_order1)
        self.post_invoice(vat_invoice_1, invoice_date=date_01)

        docs = self.generate_vat_documents_by_partner(partner, date_01, date_01)

        sale_order2 = self.create_sale_order(
            partner,
            [product_11],
            [15],
            [2000.0],
            date_order=date_01,
        )
        self.confirm_sale_order(sale_order2, date_order=date_01)

        vat_invoice_2 = self.create_invoice(partner, [product_11], [30000], date=date_01, sale_order=sale_order2)
        self.post_invoice(vat_invoice_2, invoice_date=date_01)

        docs = self.generate_vat_documents_by_partner(partner, date_01, date_01)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(vat_invoice_2),
            [
                (product_11, 30000, 15, 5000),
            ],
            "Invoice tax invoice",
        )
