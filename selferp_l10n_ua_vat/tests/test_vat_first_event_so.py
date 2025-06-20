from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_vat.tests.common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVATFirstEventSaleOrder(VATTestCommon):

    def test_vat_first_event_with_sale_orders_case_1(self):
        event_date_01 = datetime(2023, 3, 1)
        event_date_02 = datetime(2023, 3, 2)
        event_date_03 = datetime(2023, 3, 3)

        partner = self.env['res.partner'].create({
            'name': "ТОВ \"Веселка\"",
            'tracking_first_event': 'by_order',
        })

        product_1 = self.env['product.product'].create({
            'name': 'product_1',
            'uom_id': self.uom_unit_id,
            'lst_price': 15000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })
        product_2 = self.env['product.product'].create({
            'name': 'product_2',
            'uom_id': self.uom_unit_id,
            'lst_price': 21000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        sale_order_1 = self.create_sale_order(
            partner,
            [product_1, product_2],
            [1,         1],
            [15000.0,   21000.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order_1, date_order=event_date_01)

        pay_1_l1 = self.create_contract_bank_statement_line(partner, 12000, sale_order=sale_order_1, date=event_date_02)
        pay_1 = self.validate_statement_line(pay_1_l1)

        invoice_1 = self.invoicing_sale_order(sale_order_1)
        self.post_invoice(invoice_1, invoice_date=event_date_03)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.check_vat_invoice(pay_1, 12000.0, "First payment")
        self.check_vat_invoice(invoice_1, 24000.0, "First invoice")

        self.assertTrue(self.get_vat_invoice_1(pay_1))
        self.assertTrue(self.get_vat_invoice_1(invoice_1))

        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '643200', 'debit', self.vat_of(12000))
        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '641200', 'credit', self.vat_of(12000))

        factor = 12000 / 36000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_1),
            [
                (product_1, *self.calc_vat_line_params(15000, 1, factor=factor)),
                (product_2, *self.calc_vat_line_params(21000, 1, factor=factor)),
            ],
            "Tax invoice 1",
        )

        self.check_move_line_account(self.get_vat_invoice_1(invoice_1), '643200', 'debit', self.vat_of(24000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice_1), '641200', 'credit', self.vat_of(24000))

        factor = 24000 / 36000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice_1),
            [
                (product_1, *self.calc_vat_line_params(15000, 1, factor=factor)),
                (product_2, *self.calc_vat_line_params(21000, 1, factor=factor)),
            ],
            "Tax invoice 2",
        )

        sale_order_2 = self.create_sale_order(
            partner,
            [product_1],
            [1],
            [18000.0],
            date_order=event_date_02,
        )
        self.confirm_sale_order(sale_order_2, date_order=event_date_02)

        invoice_2 = self.invoicing_sale_order(sale_order_2)
        self.post_invoice(invoice_2, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.check_vat_invoice(invoice_2, 18000.0, "Second invoice")

        self.assertTrue(self.get_vat_invoice_1(invoice_2))

        self.check_move_line_account(self.get_vat_invoice_1(invoice_2), '643200', 'debit', self.vat_of(18000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice_2), '641200', 'credit', self.vat_of(18000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice_2),
            [
                (product_1, 18000, 1, self.vat_of(18000)),
            ],
            "Tax invoice 3",
        )

    def test_vat_first_event_with_sale_orders_case_2(self):
        event_date_01 = datetime(2023, 3, 5)
        event_date_02 = datetime(2023, 3, 6)
        event_date_03 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': "ТОВ \"Alpha\"",
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': "product_7",
            'uom_id': self.uom_unit_id,
            'lst_price': 3000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [3000.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order)
        self.post_invoice(invoice, invoice_date=event_date_02)

        pay_ln = self.create_contract_bank_statement_line(partner, 30000.0, date=event_date_03, sale_order=sale_order)
        pay = self.validate_statement_line(pay_ln)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        # TODO: Check if both of payment and invoice must have reference to vat invoice (because case description says vat invoice must be the one)
        # self.assertTrue(pay.vat_invoice_id)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(30000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(30000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 30000, 10, self.vat_of(30000)),
            ],
            "Tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_3(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 4)
        event_date_03 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Протон"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'product_8',
            'uom_id': self.uom_unit_id,
            'lst_price': 3600,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [3600.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_ln = self.create_contract_bank_statement_line(partner, 30000.0, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_ln)

        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order)
        self.post_invoice(invoice, invoice_date=event_date_03)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.assertTrue(self.get_vat_invoice_1(invoice))

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', self.vat_of(30000))
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', self.vat_of(30000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 30000, 10 * 30000 / 36000, self.vat_of(30000)),
            ],
            "Tax invoice 1",
        )

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(36000 - 30000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(36000 - 30000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, (36000 - 30000), 10 * (1 - 30000 / 36000), self.vat_of(36000 - 30000)),
            ],
            "Tax invoice 2",
        )

    #TODO: Add routines to create vat_invoice (Or corrction) manualy
    def no_test_vat_first_event_with_sale_orders_case_4(self):
        event_date_01 = datetime(2023, 3, 4)
        event_date_02 = datetime(2023, 3, 5)
        event_date_03 = datetime(2023, 3, 20)
        event_date_04 = datetime(2023, 3, 21)
        event_date_05 = datetime(2023, 3, 22)
        event_date_06 = datetime(2023, 3, 23)
        event_date_07 = datetime(2023, 3, 24)
        event_date_08 = datetime(2023, 3, 31)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Кратос"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.uom_unit_id,
            'lst_price': 6000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [6000.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_ln_1 = self.create_contract_bank_statement_line(partner, 12000.0, date=event_date_02, sale_order=sale_order)
        pay_1 = self.validate_statement_line(pay_ln_1)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(pay_1))

        self.post_invoice(self.get_vat_invoice_1(pay_1), invoice_date=event_date_03)

        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '643200', 'debit', 2000)
        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '641200', 'credit', 2000)

        factor = 12000 / 60000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_1),
            [
                (product, *self.calc_vat_line_params(6000, 10, factor=factor)),
            ],
            "Payment",
        )

        # TODO: check if this feature is implemented
        # check_sale_order_product_vat_invoiced_quantity(sale_order, product, 2)

        sale_order.action_cancel()
        sale_order.action_draft()
        sale_order.order_line[0].price_unit = 5400.0
        self.confirm_sale_order(sale_order, date_order=event_date_04)
        self.deliver_sale_order(sale_order)

        refund = self.refund_vat_invoice(self.get_vat_invoice_1(pay_1))
        self.post_invoice(refund, invoice_date=event_date_04)

        # TODO: refund checking must be created here !!!

        # TODO: check if this feature is implemented
        # check_sale_order_product_vat_invoiced_quantity(sale_order, product, 2.2222)

        invoice = self.invoicing_sale_order(sale_order=sale_order, date=event_date_05)
        self.post_invoice(invoice, invoice_date=event_date_05)

        pay_ln_2 = self.create_contract_bank_statement_line(partner, 54000, sale_order=sale_order, date=event_date_06)
        pay_2 = self.validate_statement_line(pay_ln_2)

        pay_ln_3 = self.create_contract_bank_statement_line(partner, -44400, sale_order=sale_order, date=event_date_07)
        pay_3 = self.validate_statement_line(pay_ln_3)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_07)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 1600)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 1600)

        factor = 21600 / 54000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_1),
            [
                (product, *self.calc_vat_line_params(5400, 10, factor=factor)),
            ],
            "Invoice",
        )

        self.check_move_line_account(self.get_vat_invoice_1(pay_2), '643200', 'debit', 7400)
        self.check_move_line_account(self.get_vat_invoice_1(pay_2), '641200', 'credit', 7400)

        factor = 44400 / 54000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_1),
            [
                (product, *self.calc_vat_line_params(5400, 10, factor=factor)),
            ],
            "Invoice",
        )

        # TODO: Check it (reversal of payment 2 ?)
        self.check_move_line_account(self.get_vat_invoice_1(pay_3), '643200', 'credit', 7400)
        self.check_move_line_account(self.get_vat_invoice_1(pay_3), '641200', 'debit', 7400)

        factor = - 44400 / 54000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_3),
            [
                (product, *self.calc_vat_line_params(5400, 10, factor=factor)),
            ],
            "Invoice",
        )

        # TODO: check if this feature is implemented
        # check_sale_order_product_vat_invoiced_quantity(sale_order, product, 4)

    def test_vat_first_event_with_sale_orders_case_5(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 5)

        partner = self.env['res.partner'].create({
            'name': 'Зелена миля',
            'tracking_first_event': 'by_order',
        })

        product_1 = self.env['product.product'].create({
            'name': 'Буряк',
            'uom_id': self.uom_unit_id,
            'lst_price': 24.0,
            'taxes_id': [Command.link(self.default_tax.id)],
        })
        product_2 = self.env['product.product'].create({
            'name': 'Овес',
            'uom_id': self.uom_unit_id,
            'lst_price': 17.1,
            'taxes_id': [Command.link(self.tax_sale_14.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product_1, product_2],
            [20, 10],
            [24.00, 17.10],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        amount1 = 24 * 20
        amount2 = 17.1 * 10

        self.check_move_line(invoice, '701000', product_1, 'credit', self.without_vat(amount1), 20)
        self.check_move_line(invoice, '701000', product_2, 'credit', self.without_vat(amount2, self.tax_sale_14), 10)

        self.check_move_line_account(invoice, '643100', 'credit', self.vat_of(amount1))
        self.check_move_line_account(invoice, '643100', 'credit', self.vat_of(amount2, self.tax_sale_14))
        self.check_move_line_account(invoice, '361000', 'debit', amount1 + amount2)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.check_vat_invoice(invoice, amount1 + amount2, 'Invoice')
        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(amount1))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit',
                                     self.vat_of(amount2, self.tax_sale_14))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit',
                                     self.vat_of(amount1) + self.vat_of(amount2, self.tax_sale_14))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product_1, *self.calc_vat_line_params(24, 20)),
                (product_2, *self.calc_vat_line_params(17.1, 10, tax=self.tax_sale_14)),
            ],
            "Tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_6(self):
        event_date_01 = datetime(2023, 3, 13)
        event_date_02 = datetime(2023, 3, 14)
        event_date_03 = datetime(2023, 3, 15)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Ромашка"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.uom_unit_id,
            'lst_price': 24,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [40],
            [24.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_line = self.create_contract_bank_statement_line(partner, 1920, sale_order=sale_order, date=event_date_02)
        pay = self.validate_statement_line(pay_line)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', self.vat_of(1920))
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', self.vat_of(1920))

        factor = 1920 / (24 * 40)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 1920, 40 * factor, self.vat_of(1920)),
            ],
            "Tax invoice",
        )

        sale_order.action_cancel()
        sale_order.action_draft()
        sale_order.order_line[0].product_uom_qty = 80
        self.confirm_sale_order(sale_order, date_order=event_date_03)

        self.deliver_sale_order(sale_order)
        invoice = self.invoicing_sale_order(sale_order, date=event_date_03)
        self.post_invoice(invoice, invoice_date=event_date_03)

    def test_vat_first_event_with_sale_orders_case_7(self):
        event_date_01 = datetime(2023, 3, 1)
        event_date_02 = datetime(2023, 3, 2)
        event_date_03 = datetime(2023, 3, 3)
        event_date_04 = datetime(2023, 3, 4)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Мрія"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.uom_unit_id,
            'lst_price': 2400,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [2400.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        invoice = self.invoicing_sale_order(sale_order)

        self.post_invoice(invoice, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.check_vat_invoice(invoice, 24000, "Invoice")

        refund = self.refund_invoice_partly(invoice, [product], [5], event_date_03)

        self.post_invoice(refund, invoice_date=event_date_03)

        self.check_first_event(refund, -12000, "Refund first event")

        self.generate_vat_documents(self.env.company.id, event_date_02, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(refund))

        self.check_vat_invoice(refund, -12000, "Refund")

        bank_line = self.create_bank_statement_line(partner, -12000, ref='payment', date=event_date_04)

        #self.validate_statement_line(bank_line, invoice=refund)

        docs = self.generate_vat_documents_by_partner(partner, event_date_03, event_date_04)

        self.assertEqual(len(docs), 0)

    def test_vat_first_event_with_sale_orders_case_8(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_order',
        })

        self.tax_sale_20.include_base_amount = True

        product = self.env['product.product'].create({
            'name': 'Цигарки',
            'uom_id': self.uom_unit_id,
            'lst_price': 252.0,
            'taxes_id': [Command.link(self.tax_sale_20.id), Command.link(self.tax_5_sale_incl.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [20],
            [252.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice), 'No vat invoice')
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_01)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 5040, 20, self.vat_of(5040 - 5040 * (1 - 1 / 1.05))),
            ],
            "Tax invoice",
        )

        pay_line = self.create_contract_bank_statement_line(partner, 5040, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        self.check_first_event(pay, 0, "Pay first event")

    def test_vat_first_event_with_sale_orders_case_9(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_order',
        })

        self.tax_sale_20.include_base_amount = True

        product = self.env['product.product'].create({
            'name': 'Цигарки',
            'uom_id': self.uom_unit_id,
            'lst_price': 252.0,
            'taxes_id': [Command.link(self.tax_sale_20.id), Command.link(self.tax_5_sale_incl.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [20],
            [252.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 5040, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        pay_first_event = self.calc_first_event_by_move(pay)
        pay_first_event_amount = pay_first_event and pay_first_event.get('amount_first_event') or 0.0
        self.assertEqual(pay_first_event_amount, 5040, "Payment first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', self.vat_of(5040 / 1.05))
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', self.vat_of(5040 / 1.05))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 5040, 20, self.vat_of(5040 / 1.05)),
            ],
            "Payment tax invoice",
        )

        # TODO: check tax invoice has no excise lines

        self.deliver_sale_order(sale_order)
        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        # TODO: check invoice contains vat and excise lines

        invoice_first_event = self.calc_first_event_by_move(invoice)
        invoice_first_event_amount = invoice_first_event and invoice_first_event.get('amount_first_event') or 0.0
        self.assertEqual(invoice_first_event_amount, 0.0, "Payment first event")

    def test_vat_first_event_with_sale_orders_case_10(self):
        event_date_01 = datetime(2023, 3, 6)
        event_date_02 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_order',
        })

        self.tax_sale_20.include_base_amount = True

        product = self.env['product.product'].create({
            'name': 'Цигарки',
            'uom_id': self.uom_unit_id,
            'lst_price': 252.0,
            'taxes_id': [Command.link(self.tax_sale_20.id), Command.link(self.tax_5_sale_incl.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [20],
            [126.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 1260, date=event_date_01, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay))

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', 200)
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', 200)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 1260, 10, 200),
            ],
            "Payment tax invoice",
        )

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 200)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 200)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 1260, 10, 200),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_11(self):
        event_date_01 = datetime(2023, 3, 6)
        event_date_02 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Фірман"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'Товар 11',
            'uom_id': self.uom_unit_id,
            'lst_price': 110.50,
            'taxes_id': [Command.link(self.tax_sale_20_exclude.id)],
        })

        self.env['product.pricelist'].create({
            'name': 'Discount',
            'item_ids': [Command.create({
                'applied_on': '0_product_variant',
                'product_id': product.id,
                'base': 'list_price',
                'compute_price': 'percentage',
                'percent_price': 5.0,
            })]
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [5],
            [110.50],
            date_order=event_date_01,
            discounts=[5]
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        pay_line = self.create_contract_bank_statement_line(partner, 629.86, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        self.assertFalse(self.get_vat_invoice_1(pay))

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 104.98)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 104.98)

        # !!! Invoice got 2 cents over because 110.5 * 0.95 = 104.975, not 104.98 ;)
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 524.88, 5, 104.98),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_12(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Тополя"',
            'tracking_first_event': 'by_order',
        })

        product = self.env['product.product'].create({
            'name': 'Товар 15',
            'uom_id': self.uom_unit_id,
            'lst_price': 50,
            'taxes_id': [Command.link(self.tax_sale_0.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [50],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        # Case description statements that it must be both debit and credit lines, since in reality it's false
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 0)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 0)

        # TODO: check if it must be any vat lines in vat invoice when vat amount is 0
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 500, 10, 0),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_13(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)
        event_date_03 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Даринка"',
            'tracking_first_event': 'by_order',
        })

        tax_vat_free = self.tax_sale_free
        # NOT IMPLEMENTED YET!
        # self.assertEqual(tax_vat_free.tax_group_id.vat_code, '903')

        product1 = self.env['product.product'].create({
            'name': 'Молоко сухе вітамінізоване "Дієта"',
            'uom_id': self.uom_unit_id,
            'lst_price': 50,
            'taxes_id': [Command.link(tax_vat_free.id)],
        })

        product2 = self.env['product.product'].create({
            'name': 'Каша "Селянська"',
            'uom_id': self.uom_unit_id,
            'lst_price': 30,
            'taxes_id': [Command.link(tax_vat_free.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product1, product2],
            [10, 10],
            [50, 30],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        invoice_first_event = self.calc_first_event_by_move(invoice)
        invoice_first_event_amount = invoice_first_event and invoice_first_event.get('amount_first_event') or 0.0
        self.assertEqual(invoice_first_event_amount, 800, "Invoice first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        # Case description statements that it must be both debit and credit lines, since in reality it's false
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 0)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 0)

        # TODO: check if it must be any vat lines in vat invoice when vat amount is 0
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product1, 500, 10, 0),
                (product2, 300, 10, 0),
            ],
            "Invoice tax invoice",
        )

        pay_line = self.create_contract_bank_statement_line(partner, 800, sale_order=sale_order, date=event_date_03)
        pay = self.validate_statement_line(pay_line)

        pay_first_event = self.calc_first_event_by_move(pay)
        pay_first_event_amount = pay_first_event and pay_first_event.get('amount_first_event') or 0.0
        self.assertEqual(pay_first_event_amount, 0, "Payment first event")

    def test_vat_first_event_with_sale_orders_case_14(self):
        event_date_01 = datetime(2023, 3, 15)
        event_date_02 = datetime(2023, 3, 16)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Даринка"',
            'tracking_first_event': 'by_order',
        })

        tax_vat_free = self.tax_sale_free
        # NOT IMPLEMENTED YET!
        # self.assertEqual(tax_vat_free.tax_group_id.vat_code, '903')

        product1 = self.env['product.product'].create({
            'name': 'Молоко сухе вітамінізоване "Дієта"',
            'uom_id': self.uom_unit_id,
            'lst_price': 50,
            'taxes_id': [Command.link(tax_vat_free.id)],
        })

        product2 = self.env['product.product'].create({
            'name': 'Каша "Селянська"',
            'uom_id': self.uom_unit_id,
            'lst_price': 30,
            'taxes_id': [Command.link(tax_vat_free.id)],
        })

        product3 = self.env['product.product'].create({
            'name': 'Буряк',
            'uom_id': self.uom_unit_id,
            'lst_price': 20,
            'taxes_id': [Command.link(self.tax_sale_20_exclude.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product1, product2, product3],
            [10, 10, 20],
            [50, 30, 20],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 1280, sale_order=sale_order, date=event_date_02)
        pay = self.validate_statement_line(pay_line)

        vat_invoices = self.generate_vat_documents_by_partner(partner, event_date_01, event_date_02)

        # Check if two vat documents must be created
        # self.assertTrue(len(vat_invoices), 2)

        # it uses wrong tax base, computes wrong products counts etc. so next two checks fail
        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', 80)
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', 80)

        # it fails too (bad vat_line_ids)
        self.check_vat_invoice_lines(
            vat_invoices[0],
            [
                (product3, 400, 20, 80),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_sale_orders_case_different_tax_variant(self):
        event_date_01 = datetime(2023, 3, 1)
        event_date_02 = datetime(2023, 3, 2)
        event_date_03 = datetime(2023, 3, 3)
        event_date_04 = datetime(2023, 3, 4)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Мрія"',
            'tracking_first_event': 'by_order',
        })

        product_1 = self.env['product.product'].create({
            'name': 'product_a',
            'uom_id': self.uom_unit_id,
            'lst_price': 1200,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        product_2 = self.env['product.product'].create({
            'name': 'product_і',
            'uom_id': self.uom_unit_id,
            'lst_price': 1000,
            'taxes_id': [Command.link(self.tax_sale_20_exclude.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product_1,  product_2],
            [1,          1],
            [1200.0,     1000.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        invoice = self.invoicing_sale_order(sale_order)

        self.post_invoice(invoice, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.check_vat_invoice(invoice, 2400, "Invoice")

        """refund = self.refund_invoice_partly(invoice, [product], [5], event_date_03)

        self.post_invoice(refund)

        refund_first_event = self.calc_first_event_by_move(refund)
        refund_first_event_amount = refund_first_event and refund_first_event['amount_first_event'] or 0.0
        self.assertEqual(refund_first_event_amount, -12000, "Refund first event")

        self.generate_vat_documents(self.env.company.id, event_date_02, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(refund))

        self.check_vat_invoice(refund, -12000, "Refund")

        bank_line = self.create_bank_statement_line(partner, -1200, ref='payment', date=event_date_04)

        #self.validate_statement_line(bank_line, invoice=refund)

        docs = self.generate_vat_documents_by_partner(partner, event_date_03, event_date_04)

        self.assertEqual(len(docs), 0)"""

