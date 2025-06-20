from datetime import datetime

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tests.common import Form

from .common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVATInvoice(VATTestCommon):

    def test_vat_first_event(self):
        date_01 = datetime.strptime('2023-03-01', '%Y-%m-%d').date()
        date_02 = datetime.strptime('2023-03-02', '%Y-%m-%d').date()
        date_03 = datetime.strptime('2023-03-03', '%Y-%m-%d').date()
        date_04 = datetime.strptime('2023-03-04', '%Y-%m-%d').date()
        date_06 = datetime.strptime('2023-03-06', '%Y-%m-%d').date()
        date_15 = datetime.strptime('2023-03-15', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': "My partner",
            'tracking_first_event': 'in_general',
        })

        #product = self.env['product.product'].create({
        #    'name': 'product_a',
        #    'uom_id': self.env.ref('uom.product_uom_unit').id,
        #    'lst_price': 0,
        #    'standard_price': 800.0,
        #    #'property_account_income_id': cls.company_data['default_account_revenue'].id,
        #    #'property_account_expense_id': cls.company_data['default_account_expense'].id,
        #    'supplier_taxes_id': [],
        #})

        so = self.create_sale_order(
            partner,
            [self.product_a,    self.product_b],
            [1,                 1],
            [30000.00,          45000.00],
        )

        pay_1_l = self.create_contract_bank_statement_line(
            partner=partner,
            amount=10000,
            sale_order=so,
            date=date_01,
        )

        pay_1 = self.validate_statement_line(pay_1_l)

        pay_2_l = self.create_contract_bank_statement_line(
            partner=partner,
            amount=15000,
            date=date_02,
            sale_order=so,
        )
        pay_2 = self.validate_statement_line(pay_2_l)

        pay_3_l = self.create_contract_bank_statement_line(
            partner=partner,
            amount=40000,
            date=date_06,
            sale_order=so,
        )
        pay_3 = self.validate_statement_line(pay_3_l)

        pay_4_l = self.create_contract_bank_statement_line(
            partner=partner,
            amount=30000,
            date=date_06,
            sale_order=so,
        )
        pay_4 = self.validate_statement_line(pay_4_l)

        invoice_1 = self.create_sale_order_invoice(
            so=so,
            partner=partner,
            products=[self.product_a],
            amounts=[25000],
            taxes=[],
            date=date_03,
        )
        self.post_invoice(invoice_1)

        invoice_2 = self.create_sale_order_invoice(
            so=so,
            partner=partner,
            products=[self.product_b],
            amounts=[37500],
            taxes=[],
            date=date_04,
        )
        self.post_invoice(invoice_2)

        self.check_first_event(pay_1, 10000, "First payment")
        self.check_first_event(pay_2, 15000, "Second payment")
        self.check_first_event(invoice_1, 0, "First invoice")
        self.check_first_event(invoice_2, 37500, "Second invoice")
        self.check_first_event(pay_3, 2500, "Third payment")
        self.check_first_event(pay_4, 30000, "Forth payment")

        #TODO: check if this part of test should work after all fixes
        #self.env['account.vat.calculations'].generate_vat_documents(self.env.user.company_id.id, date_01, date_15)

        #self.check_vat_invoice(pay_1, 10000, "First payment")
        #self.check_vat_invoice(pay_2, 15000, "Second payment")
        #self.check_vat_invoice(invoice_1, 5000, "First invoice")
        #self.check_vat_invoice(invoice_2, 52500, "Second invoice")
        #self.check_vat_invoice(pay_3, 0, "Third payment")
        #self.check_vat_invoice(pay_4, 12500, "Forth payment")

    def test_change_vat_invoice_stage(self):
        partner = self.env['res.partner'].create({'name': "Partner HO"})
        default_product = self.env.company.vat_default_product_id
        account_vat = self.env.company.vat_account_id
        account_vat_unconfirmed = self.env.company.vat_account_unconfirmed_id
        total = 45
        tax = self.env.company.vat_default_tax_id
        tax_amount = tax._compute_amount(total, total)
        product_lines = [Command.create({
            'product_id': default_product.id,
            'product_uom_id': default_product.uom_id.id,
            'quantity': 1,
            'price_unit': total,
            'vat_tax_id': tax.id,
            'total': total,
        })]
        vat_invoice1 = self.env['account.move'].create({
            'move_type': 'vat_invoice',
            'vat_line_ids': product_lines,
            'partner_id': partner.id,
            'date': fields.Date.from_string('2023-04-12'),
        })

        vat_invoice1.action_post()
        self.assertEqual(vat_invoice1.vat_invoice_stage, 'prepared')

        vat_invoice1.button_cancel()
        self.assertEqual(vat_invoice1.vat_invoice_stage, 'cancelled')

        vat_invoice1.button_draft()
        self.assertEqual(vat_invoice1.vat_invoice_stage, 'draft')

        vat_invoice_2 = self.env['account.move'].create({
            'move_type': 'vat_invoice',
            'vat_line_ids': product_lines,
            'partner_id': partner.id,
            'date': fields.Date.from_string('2023-04-12'),
        })
        vat_invoice_3 = self.env['account.move'].create({
            'move_type': 'vat_invoice',
            'vat_line_ids': product_lines,
            'partner_id': partner.id,
            'date': fields.Date.from_string('2023-04-12'),
        })

        vat_invoices = self.env['account.move'].browse([vat_invoice_2.id, vat_invoice_3.id])

        vat_invoices.action_post()
        self.assertTrue(all(vat_invoices.mapped(lambda x: x.vat_invoice_stage == 'prepared')))

        vat_invoices.button_cancel()
        self.assertTrue(all(vat_invoices.mapped(lambda x: x.vat_invoice_stage == 'cancelled')))

        vat_invoices.button_draft()
        self.assertTrue(all(vat_invoices.mapped(lambda x: x.vat_invoice_stage == 'draft')))

    def test_vat_non_payer(self):
        partner = self.env['res.partner'].create({
            'name': "Partner HO",
            'vat': '121212121212',
        })
        vat_invoice1 = self.env['account.move'].create({
            'move_type': 'vat_invoice',
            'partner_id': partner.id,
            'date': fields.Date.from_string('2023-05-02'),
        })

        form = Form(vat_invoice1)
        self.assertEqual(form.vat, '121212121212')

        form.not_issued_to_customer = True
        form.reason_type = '03'
        self.assertEqual(form.vat, '400000000000')

        form.reason_type = '04'
        self.assertEqual(form.vat, '600000000000')

        form.reason_type = '07'
        self.assertEqual(form.vat, '300000000000')

        form.not_issued_to_customer = False
        self.assertFalse(form.reason_type)
        self.assertEqual(form.vat, '121212121212')

        partner = self.env['res.partner'].create({
            'name': "Partner non payer HO",
            'vat': '121212121213',
            'vat_non_payer': True,
        })

        form.partner_id = partner
        self.assertTrue(form.not_issued_to_customer)
        self.assertEqual(form.reason_type, '02')
        self.assertEqual(form.vat, '100000000000')

        form.reason_type = '03'
        self.assertEqual(form.vat, '400000000000')

        form.reason_type = '04'
        self.assertEqual(form.vat, '600000000000')

        form.reason_type = '07'
        self.assertEqual(form.vat, '300000000000')

    def test_vat_invoice_no_so(self):
        date_01 = datetime.strptime('2023-03-01', '%Y-%m-%d').date()

        partner = self.env['res.partner'].create({
            'name': "My partner",
            'tracking_first_event': 'by_order',
        })

        pay_1_l = self.create_contract_bank_statement_line(
            partner=partner,
            amount=10000,
            date=date_01,
        )

        pay_1 = self.validate_statement_line(pay_1_l)

        self.check_first_event(pay_1, 10000, "Payment first event")

        documents = self.env['account.vat.calculations'].generate_vat_documents_by_partners([partner.id], date_01, date_01)

        self.assertEqual(len(documents), 1, "Must generate 1 vat invoice")

        self.assertEqual(documents[0].partner_id, partner)
        self.assertEqual(documents[0].date, date_01)
        self.assertEqual(len(documents[0].vat_line_ids), 1, "Must generate 1 vat line")

        self.assertEqual(documents[0].vat_line_ids[0].product_id, self.env.company.vat_default_product_id)
        self.assertEqual(documents[0].vat_line_ids[0].price_unit, 10000)
        self.assertEqual(documents[0].vat_line_ids[0].vat_tax_id, self.default_tax)
