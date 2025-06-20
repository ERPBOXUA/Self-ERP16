from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged
from odoo.tools import float_compare, float_round

from odoo.addons.selferp_l10n_ua_vat.tests.common import VATTestCommonPriceVATIncl


@tagged('-at_install', 'post_install')
class TestVATFirstEventContracts(VATTestCommonPriceVATIncl):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        result = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        if result:
            company = result.get('company')
            if company:
                account_sale_tax_id = cls.env['account.tax'].search(
                    [
                        ('type_tax_use', '=', 'sale'),
                        ('company_id', '=', company.id),
                        ('price_include', '=', True),
                    ],
                    limit=1
                )
                account_purchase_tax_id = cls.env['account.tax'].search(
                    [
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id', '=', company.id),
                        ('price_include', '=', True),
                    ],
                    limit=1
                )
                company.write({
                    'account_sale_tax_id': account_sale_tax_id.id,
                    'account_purchase_tax_id': account_purchase_tax_id.id,
                })
                result.update({
                    'default_tax_sale': account_sale_tax_id,
                    'default_tax_purchase': account_purchase_tax_id,
                })
        return result

    def test_vat_first_event_with_contracts_case_1(self):
        event_date_01 = datetime(2023, 3, 1)
        event_date_02 = datetime(2023, 3, 2)
        event_date_03 = datetime(2023, 3, 3)

        product_1 = self.env['product.product'].create({
            'name': 'product_1',
            'uom_id': self.uom_unit_id,
            'lst_price': 15000,
        })
        product_2 = self.env['product.product'].create({
            'name': 'product_2',
            'uom_id': self.uom_unit_id,
            'lst_price': 21000,
        })

        partner = self.env['res.partner'].create({
            'name': "My partner",
            'tracking_first_event': 'by_contract',
        })

        contract_1 = self.create_contract("contract_1", partner, 'sale')
        contract_2 = self.create_contract("contract_2", partner, 'sale')

        c1_sale_order_1 = self.create_sale_order(
            partner,
            [product_1, product_2],
            [1,         1],
            [15000.00,  21000.00],
            contract_1,
            date_order=event_date_01,
        )
        self.confirm_sale_order(c1_sale_order_1)
        self.deliver_sale_order(c1_sale_order_1)

        pay_1_l1 = self.create_contract_bank_statement_line(partner, 12000, contract=contract_1, sale_order=c1_sale_order_1, date=event_date_02)

        pay_1 = self.validate_statement_line(pay_1_l1)

        invoice_1 = self.invoicing_sale_order(c1_sale_order_1)
        self.post_invoice(invoice_1, invoice_date=event_date_03)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.check_vat_invoice(pay_1, 12000.0, "First payment")
        self.check_vat_invoice(invoice_1, 24000.0, "First invoice")

        self.assertTrue(self.get_vat_invoice_1(pay_1))
        self.assertTrue(self.get_vat_invoice_1(invoice_1))

        self.post_invoice(self.get_vat_invoice_1(pay_1), invoice_date=event_date_03)

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

        self.post_invoice(self.get_vat_invoice_1(invoice_1))

        self.check_move_line_account(self.get_vat_invoice_1(invoice_1), '643200', 'debit', self.vat_of(24000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice_1), '641200', 'credit', self.vat_of(24000))

        factor = 1 - factor

        self.check_vat_invoice_lines(
           self.get_vat_invoice_1(invoice_1),
           [
               (product_1, *self.calc_vat_line_params(15000, 1, factor=factor)),
               (product_2, *self.calc_vat_line_params(21000, 1, factor=factor)),
           ],
           "Tax invoice 2",
        )

        # TODO discus rest of test

        c2_sale_order_2 = self.create_sale_order(
            partner,
            [product_1],
            [1],
            [18000.00],
            contract_2,
            date_order=event_date_02,
        )
        self.confirm_sale_order(c2_sale_order_2)
        self.deliver_sale_order(c2_sale_order_2)

        invoice_2 = self.invoicing_sale_order(c2_sale_order_2, date=event_date_02)
        self.post_invoice(invoice_2, invoice_date=event_date_02)

        # Dates?
        self.generate_vat_documents(self.env.company.id, event_date_02, event_date_02)

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

    def test_vat_first_event_with_contracts_case_2(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 5)

        product_1 = self.env['product.product'].create({
            'name': 'Буряк',
            'uom_id': self.uom_unit_id,
            'lst_price': 24.0,
        })
        product_2 = self.env['product.product'].create({
            'name': 'Овес',
            'uom_id': self.uom_unit_id,
            'lst_price': 17.1,
            'taxes_id': [Command.link(self.tax_sale_14.id)],
        })

        partner = self.env['res.partner'].create({
            'name': 'Зелена миля',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('contract', partner, 'sale')

        sale_order = self.create_sale_order(
            partner,
            [product_1, product_2],
            [20,        10],
            [24.00,     17.10],
            contract,
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
        self.check_move_line_account(invoice, '361000', 'debit', amount1+amount2)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.check_vat_invoice(invoice, amount1 + amount2, 'Invoice')
        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(amount1))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(amount2, self.tax_sale_14))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(amount1) + self.vat_of(amount2, self.tax_sale_14))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product_1, *self.calc_vat_line_params(24, 20)),
                (product_2, *self.calc_vat_line_params(17.1, 10, tax=self.tax_sale_14)),
            ],
            "Tax invoice",
        )

    def test_vat_first_event_with_contracts_case_3(self):
        event_date_01 = datetime(2023, 3, 13)
        event_date_02 = datetime(2023, 3, 14)
        event_date_03 = datetime(2023, 3, 15)

        product = self.env['product.product'].create({
            'name': 'Product 1',
            'uom_id': self.uom_unit_id,
            'lst_price': 24.0,
        })

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Ромашка"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('contract', partner, 'sale')

        sale_order = self.create_sale_order(
            partner,
            [product],
            [40],
            [24.00],
            contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_1_l1 = self.create_contract_bank_statement_line(partner, 1920, contract=contract, sale_order=sale_order, date=event_date_02)

        pay_1 = self.validate_statement_line(pay_1_l1)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(pay_1))
        self.post_invoice(self.get_vat_invoice_1(pay_1), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '643200', 'debit', self.vat_of(1920))
        self.check_move_line_account(self.get_vat_invoice_1(pay_1), '641200', 'credit', self.vat_of(1920))

        factor = 1920 / (24 * 40)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_1),
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

    def test_vat_first_event_with_contract_case_4(self):
        event_date_01 = datetime(2023, 3, 4)
        event_date_02 = datetime(2023, 3, 30)
        event_date_03 = datetime(2023, 4, 2)

        product = self.env['product.product'].create({
            'name': 'Product 4',
            'uom_id': self.uom_unit_id,
            'lst_price': 2400.0,
        })

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Мрія"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№23', partner, contract_date=event_date_01)

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [2400.0],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_01)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_01)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(24000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(24000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, *self.calc_vat_line_params(2400, 10)),
            ],
            "Invoice",
        )

        refund = self.refund_invoice_partly(invoice, [product], [5], date_refund=event_date_02)
        self.post_invoice(refund, invoice_date=event_date_02)

        refund_first_event = self.calc_first_event_by_move(refund)
        refund_first_event_amount = refund_first_event and refund_first_event['amount_first_event'] or 0.0
        self.assertEqual(refund_first_event_amount, -12000, "Refund first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(refund))
        self.post_invoice(self.get_vat_invoice_1(refund), invoice_date=event_date_02)

        # TODO: Check it (correction without vat lines?)
        factor = - 12000 / 24000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(refund),
            [
                (product, *self.calc_vat_line_params(2400, 10, factor=factor)),
            ],
            "Payment back",
        )

        refund_pay_line = self.create_contract_bank_statement_line(partner, -1000, contract=contract, date=event_date_03)
        # TODO: This fails with message 'You are trying to reconcile some entries that are already reconciled'
        # refund_pay = self.validate_statement_line(refund_pay_line, invoice=refund)
        refund_pay = self.validate_statement_line(refund_pay_line)

        self.check_first_event(refund_pay, 0, "Refund pay")

        # self.generate_vat_documents(self.env.company.id, event_date_02 + timedelta(days=1), event_date_03)
        # self.assertFalse(self.get_vat_invoice_1(refund_pay), 'First event is not absent')

        docs = self.generate_vat_documents_by_partner(partner, event_date_02 + timedelta(days=1), event_date_03)
        refund_vat = self.get_vat_invoice_1(refund_pay)
        self.assertFalse(refund_vat, "First event is not absent")

    def test_vat_first_event_with_contract_case_4_discount(self):
        event_date_01 = datetime(2023, 3, 4)
        event_date_02 = datetime(2023, 3, 30)
        event_date_03 = datetime(2023, 4, 2)

        product = self.env['product.product'].create({
            'name': 'Product 4',
            'uom_id': self.uom_unit_id,
            'lst_price': 2400.0,
        })

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Мрія"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№23', partner, contract_date=event_date_01)

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [2000.0],
            discounts=[10],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_01)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_01)

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(18000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(18000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, *self.calc_vat_line_params(2000, 10, dsc=0.9)),
            ],
            "Invoice",
        )

        refund = self.refund_invoice_partly(invoice, [product], [5], date_refund=event_date_02)
        self.post_invoice(refund, invoice_date=event_date_02)

        refund_first_event = self.calc_first_event_by_move(refund)
        refund_first_event_amount = refund_first_event and refund_first_event['amount_first_event'] or 0.0
        self.assertEqual(refund_first_event_amount, -9000, "Refund first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(refund))
        self.post_invoice(self.get_vat_invoice_1(refund), invoice_date=event_date_02)

        # TODO: Check it (correction without vat lines?)
        factor = -0.5
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(refund),
            [
                (product, *self.calc_vat_line_params(2000, 10, factor=factor, dsc=0.9)),
            ],
            "Payment back",
        )

        refund_pay_line = self.create_contract_bank_statement_line(partner, -900, contract=contract, date=event_date_03)
        # TODO: This fails with message 'You are trying to reconcile some entries that are already reconciled'
        # refund_pay = self.validate_statement_line(refund_pay_line, invoice=refund)
        refund_pay = self.validate_statement_line(refund_pay_line)

        self.check_first_event(refund_pay, 0, "Refund pay")

    def test_vat_first_event_with_contract_case_5(self):
        event_date_01 = datetime(2023, 3, 1)
        event_date_02 = datetime(2023, 3, 10)
        event_date_03 = datetime(2023, 3, 15)

        product = self.env['product.product'].create({
            'name': 'product_b',
            'uom_id': self.uom_unit_id,
            'lst_price': 24000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Бета-М"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№ 467', partner, operation_type='sale', contract_date=event_date_01)

        sale_order = self.create_sale_order(
            partner,
            [product],
            [1],
            [24000],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(
            partner, 8000, contract=contract, sale_order=sale_order, date=event_date_02
        )
        pay = self.validate_statement_line(pay_line)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay), invoice_date=event_date_03)

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', self.vat_of(8000))
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', self.vat_of(8000))

        factor = 8000 / 24000
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, *self.calc_vat_line_params(24000, 1, factor=factor)),
            ],
            "Payment",
        )

        refund_pay_line = self.create_contract_bank_statement_line(
            partner, -8000, contract=contract, date=event_date_03
        )
        refund_pay = self.validate_statement_line(refund_pay_line)

        self.check_first_event(refund_pay, -8000, "Refund payment first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(refund_pay))
        self.post_invoice(self.get_vat_invoice_1(refund_pay), invoice_date=event_date_03)

        self.check_vat_invoice(refund_pay, -8000, "Refund payment")

        factor = - factor
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(refund_pay),
            [
                (product, *self.calc_vat_line_params(24000, 1, factor=factor)),
            ],
            "Refund payment",
        )

    def test_vat_first_event_with_contract_case_6(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_order',
        })

        contract = self.create_contract('№33', partner, contract_date=event_date_01)

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
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice), 'No vat invoice')
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_01)

        # TODO: check tax base when multiple taxes !!!
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 5040, 20, 800),
            ],
            "Tax invoice",
        )

        pay_line = self.create_contract_bank_statement_line(partner, 5040, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        self.check_first_event(pay, 0, "Payment first event")

    def test_vat_first_event_with_contract_case_7(self):
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№33', partner, contract_date=event_date_01)

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
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 5040, contract=contract, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        pay_first_event = self.calc_first_event_by_move(pay)
        pay_first_event_amount = pay_first_event and pay_first_event.get('amount_first_event') or 0.0
        self.assertEqual(pay_first_event_amount, 5040, "Payment first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay), invoice_date=event_date_02)

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', 800)
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', 800)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 5040, 20, 800),
            ],
            "Payment tax invoice",
        )

        # TODO: check tax invoice has no excise lines

        self.deliver_sale_order(sale_order)
        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        # TODO: check invoice contains vat and excise lines

    def test_vat_first_event_with_contract_case_8(self):
        event_date_01 = datetime(2023, 3, 6)
        event_date_02 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Форс мажор"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№33', partner, contract_date=event_date_01)

        self.tax_sale_20.include_base_amount = True

        product = self.env['product.product'].create({
            'name': 'Цигарки',
            'uom_id': self.uom_unit_id,
            'lst_price': 126.0,
            'taxes_id': [Command.link(self.tax_sale_20.id), Command.link(self.tax_5_sale_incl.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [20],
            [126.0],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 1260, contract=contract, date=event_date_01, sale_order=sale_order)
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

    def test_vat_first_event_with_contract_case_9(self):
        event_date_01 = datetime(2023, 3, 6)
        event_date_02 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Фірман"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№234-1', partner, contract_date=event_date_01)

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
            contract=contract,
            date_order=event_date_01,
            discounts=[5],
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_01)
        self.post_invoice(invoice, invoice_date=event_date_01)

        pay_line = self.create_contract_bank_statement_line(partner, 629.86, contract=contract, date=event_date_02, sale_order=sale_order)
        pay = self.validate_statement_line(pay_line)

        self.check_first_event(invoice, 629.86, "Invoice first event")

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_02)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', 104.98)
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', 104.98)

        self.assertFalse(self.get_vat_invoice_1(pay))

        # !!! Invoice got 2 cents over because 110.5 * 0.95 = 104.975, not 104.98 ;)
        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 524.88, 5, 104.98),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_contract_case_10(self):
        event_date_00 = datetime(2023, 2, 1)
        event_date_01 = datetime(2023, 3, 5)
        event_date_02 = datetime(2023, 3, 6)
        event_date_03 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Ромашка"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№234-1', partner, contract_date=event_date_00)

        product = self.env['product.product'].create({
            'name': 'Товар 7',
            'uom_id': self.uom_unit_id,
            'lst_price': 3000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [3000],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        invoice = self.invoicing_sale_order(sale_order, date=event_date_02)
        self.post_invoice(invoice, invoice_date=event_date_02)

        pay_line = self.create_contract_bank_statement_line(partner, 30000, contract=contract, sale_order=sale_order, date=event_date_03)
        pay = self.validate_statement_line(pay_line)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice))

        self.assertFalse(self.get_vat_invoice_1(pay))

        self.check_move_line_account(self.get_vat_invoice_1(invoice), '643200', 'debit', self.vat_of(30000))
        self.check_move_line_account(self.get_vat_invoice_1(invoice), '641200', 'credit', self.vat_of(30000))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 30000, 10, self.vat_of(30000)),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_contract_case_11(self):
        event_date_00 = datetime(2023, 1, 1)
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Тополя"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№152', partner, contract_date=event_date_00)

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
            contract=contract,
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

    def test_vat_first_event_with_contract_case_12(self):
        event_date_00 = datetime(2023, 1, 1)
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 6)
        event_date_03 = datetime(2023, 3, 9)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Даринка"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№12', partner, contract_date=event_date_00)

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
            contract=contract,
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

        pay_line = self.create_contract_bank_statement_line(partner, 800, contract=contract, sale_order=sale_order, date=event_date_03)
        pay = self.validate_statement_line(pay_line)

        pay_first_event = self.calc_first_event_by_move(pay)
        pay_first_event_amount = pay_first_event and pay_first_event.get('amount_first_event') or 0.0
        self.assertEqual(pay_first_event_amount, 0, "Payment first event")

    def test_vat_first_event_with_contract_case_13(self):
        event_date_00 = datetime(2023, 1, 1)
        event_date_01 = datetime(2023, 3, 15)
        event_date_02 = datetime(2023, 3, 16)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Даринка"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№12', partner, contract_date=event_date_00)

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
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)
        self.deliver_sale_order(sale_order)

        pay_line = self.create_contract_bank_statement_line(partner, 1280, contract=contract, sale_order=sale_order, date=event_date_02)
        pay = self.validate_statement_line(pay_line)

        vat_invoices = self.generate_vat_documents_by_partner(partner, event_date_01, event_date_02)

        #Check if two vat documents must be created
        self.assertTrue(len(vat_invoices), 2)

        vat_invoice_1 = self.get_vat_invoice_1(pay)

        # it uses wrong tax base, computes wrong products counts etc. so next two checks fail
        self.check_move_line_account(vat_invoice_1, '643200', 'debit', 80)
        self.check_move_line_account(vat_invoice_1, '641200', 'credit', 80)

        # it fails too (bad vat_line_ids)
        self.dump_vat_move(vat_invoice_1)
        self.check_vat_invoice_lines(
            vat_invoice_1,
            [
                (product3, 400, 20, 80),
            ],
            "Invoice tax invoice",
        )

    def test_vat_first_event_with_contract_case_14(self):
        event_date_00 = datetime(2023, 3, 1)
        event_date_01 = datetime(2023, 3, 3)
        event_date_02 = datetime(2023, 3, 4)
        event_date_03 = datetime(2023, 3, 6)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Омега"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№238-1', partner, contract_date=event_date_00)

        product = self.env['product.product'].create({
            'name': 'Товар 8',
            'uom_id': self.uom_unit_id,
            'lst_price': 3600,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [3600],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_line = self.create_contract_bank_statement_line(partner, 36000, contract=contract, sale_order=sale_order, date=event_date_02)
        pay = self.validate_statement_line(pay_line)

        self.deliver_sale_order(sale_order)
        invoice = self.invoicing_sale_order(sale_order, event_date_03)
        self.post_invoice(invoice, invoice_date=event_date_03)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(pay))
        self.post_invoice(self.get_vat_invoice_1(pay), invoice_date=event_date_03)

        self.check_move_line_account(self.get_vat_invoice_1(pay), '643200', 'debit', 6000)
        self.check_move_line_account(self.get_vat_invoice_1(pay), '641200', 'credit', 6000)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay),
            [
                (product, 36000, 10, 6000),
            ],
            "Payment tax invoice",
        )

    #TODO: Check test logic with Anton and Yrina
    def no_test_vat_first_event_with_contract_case_15(self):
        event_date_00 = datetime(2023, 2, 1)
        event_date_01 = datetime(2023, 3, 4)
        event_date_02 = datetime(2023, 3, 5)
        event_date_03 = datetime(2023, 3, 20)
        event_date_04 = datetime(2023, 3, 21)
        event_date_05 = datetime(2023, 3, 22)
        event_date_06 = datetime(2023, 3, 23)
        event_date_07 = datetime(2023, 3, 24)
        event_date_08 = datetime(2023, 3, 31)

        partner = self.env['res.partner'].create({
            'name': 'ТОВ "Злий бобер"',
            'tracking_first_event': 'by_contract',
        })

        contract = self.create_contract('№345-34', partner, contract_date=event_date_00)

        product = self.env['product.product'].create({
            'name': 'Товар А',
            'uom_id': self.uom_unit_id,
            'lst_price': 6000,
            'taxes_id': [Command.link(self.tax_sale_20.id)],
        })

        sale_order = self.create_sale_order(
            partner,
            [product],
            [10],
            [6000],
            contract=contract,
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order, date_order=event_date_01)

        pay_line1 = self.create_contract_bank_statement_line(partner, 12000, contract=contract, sale_order=sale_order, date=event_date_02)
        pay1 = self.validate_statement_line(pay_line1)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        self.assertTrue(self.get_vat_invoice_1(pay1))

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay1),
            [
                (product, 12000, 2, 2000),
            ],
            "Payment 1 tax invoice",
        )

        sale_order.action_cancel()
        sale_order.action_draft()
        sale_order.order_line[0].price_unit = 5400
        self.confirm_sale_order(sale_order, date_order=event_date_04)

        self.refund_invoice_partly(self.get_vat_invoice_1(pay1))

        # check_sale_order_product_vat_invoiced_quantity(sale_order, product, self.round_qty(2.2222))

        invoice = self.init_invoice(
            'out_invoice',
            partner,
            invoice_date=event_date_05,
            post=False,
            products=[product],
            amounts=[4*5400],
        )
        invoice.invoice_origin = sale_order.name
        self.post_invoice(invoice, invoice_date=event_date_05)

        pay_line2 = self.create_contract_bank_statement_line(partner, 54000, contract=contract, sale_order=sale_order, date=event_date_06)
        pay2 = self.validate_statement_line(pay_line2)

        pay_line_refund = self.create_contract_bank_statement_line(partner, -44400, contract=contract, sale_order=sale_order, date=event_date_07)
        pay_refund = self.validate_statement_line(pay_line_refund)

        self.generate_vat_documents(self.env.company.id, event_date_04, event_date_07)

        self.assertTrue(self.get_vat_invoice_1(invoice))
        self.post_invoice(self.get_vat_invoice_1(invoice), invoice_date=event_date_08)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(invoice),
            [
                (product, 9600, 1.7778, 1600),
            ],
            "Invoice tax invoice",
        )

        self.assertTrue(self.get_vat_invoice_1(pay2))
        self.post_invoice(self.get_vat_invoice_1(pay2), invoice_date=event_date_08)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay2),
            [
                (product, 44400, 8.2222, 7400),
            ],
            "Payment 2 tax invoice",
        )

        self.assertTrue(self.get_vat_invoice_1(pay_refund))
        self.post_invoice(self.get_vat_invoice_1(pay_refund), invoice_date=event_date_08)

        self.check_vat_invoice_lines(
            self.get_vat_invoice_1(pay_refund),
            [
                (product, -44400, 8.2222, -7400),
            ],
            "Refund tax invoice",
        )

        # check_sale_order_product_vat_invoiced_quantity(sale_order, product, 4)
