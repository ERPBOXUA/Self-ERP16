from datetime import date

from odoo import Command
from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_ext.tests.common import AccountTestCommon


@tagged('post_install', '-at_install')
class TestSaleOrderExport(AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_usd = cls.env.ref('base.USD')

        cls.partner = cls.env['res.partner'].create({
            'name': 'Exporter',
        })

        product_uom = cls.env.ref('uom.product_uom_unit')
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Холодильник',
            'uom_id': product_uom.id,
            'taxes_id': None,
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Пральна машина',
            'uom_id': product_uom.id,
            'taxes_id': None,
        })

        cls.date_1 = date(2023, 5, 7)
        cls.date_2 = date(2023, 5, 9)
        cls.date_3 = date(2023, 5, 14)

    def test_export_1(self):
        self._test_export(
            [
                {
                    'date': self.date_1,
                    'amount': 6800.0,
                    'rate': 38.0,
                },
            ],
            38.5,
            [
                95000.0,
                163400.0,
            ],
        )

    def test_export_2(self):
        self._test_export(
            [
                {
                    'date': self.date_1,
                    'amount': 3000.0,
                    'rate': 38.0,
                },
            ],
            38.5,
            [
                95698.53,
                164601.47,
            ],
        )

    def test_export_3(self):
        self._test_export(
            [
                {
                    'date': self.date_1,
                    'amount': 3000.0,
                    'rate': 38.0,
                },
                {
                    'date': self.date_2,
                    'amount': 3800.0,
                    'rate': 39.0,
                },
            ],
            38.5,
            [
                96397.06,
                165802.94,
            ],
        )

    def test_export_6(self):
        self._test_export(
            [
                {
                    'date': self.date_1,
                    'amount': 8000.0,
                    'rate': 38.0,
                },
            ],
            40,
            [
                95000.0,
                163400.0,
            ],
        )

    def test_export_7(self):
        self._test_export(
            [
                {
                    'date': self.date_1,
                    'amount': 3000.0,
                    'rate': 38.0,
                },
                {
                    'date': self.date_2,
                    'amount': 5000.0,
                    'rate': 39.0,
                },
            ],
            38.5,
            [
                96397.06,
                165802.94,
            ],
        )

    def _test_export(self, advance_info, cd_currency_rate, invoice_amounts):
        # create and confirm sale order
        sale_order = self.create_sale_order(
            self.partner,
            [self.product_1, self.product_2],
            [5, 10],
            [2500.0, 4300.0],
            date_order=self.date_1,
            currency=self.currency_usd,
        )
        self.confirm_sale_order(sale_order, date_order=self.date_1)

        # create advance payments
        payments = self.env['account.move']
        if advance_info:
            for advance in advance_info:
                bank_statement = self.create_contract_bank_statement_line(
                    partner=self.partner,
                    amount=advance['amount'] * advance['rate'],
                    date=advance['date'],
                    sale_order=sale_order,
                    currency=self.currency_usd,
                    amount_currency=advance['amount'],
                )

                payments += self.validate_statement_line(bank_statement)

        # create invoice
        invoice = self.init_invoice(
            'out_invoice',
            invoice_date=self.date_3,
            partner=self.partner,
        )

        invoice.write({
            'currency_id': self.currency_usd,
        })
        self.assertTrue(invoice.company_currency_id != self.currency_usd)

        self.assertTrue(invoice.can_be_cd)

        invoice.write({
            'is_customs_declaration': True,
            'cd_date': self.date_3,
            'cd_currency_rate': cd_currency_rate,
        })

        invoice.write({
            'line_ids': [
                Command.create({
                    'product_id': self.product_1.id,
                    'price_unit': 500,
                    'quantity': 5,
                    'tax_ids': None,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'price_unit': 430,
                    'quantity': 10,
                    'tax_ids': None,
                }),
            ],
        })

        # check advances info
        self.assertEqual(len(invoice.cd_can_be_prepayment_ids), len(payments))
        for i, payment in enumerate(payments):
            self.assertTrue(payment.line_ids[1] in invoice.cd_can_be_prepayment_ids)

        invoice.cd_prepayment_ids = invoice.cd_can_be_prepayment_ids

        # post invoice
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

        # check invoice reconciliation
        amount_payment = sum([p.amount_total for p in payments])
        paid = amount_payment >= invoice.amount_total_signed
        if paid:
            self.assertEqual(invoice.payment_state, 'paid')
        else:
            self.assertEqual(invoice.payment_state, 'partial')
        self.assertEqual(len(invoice.line_ids), 3)

        self.assertEqual(invoice.line_ids[0].product_id, self.product_1)
        self.assertEqual(invoice.line_ids[0].balance, -invoice_amounts[0])
        self.assertEqual(len(invoice.line_ids[0].matched_debit_ids), 0)
        self.assertEqual(len(invoice.line_ids[0].matched_credit_ids), 0)

        self.assertEqual(invoice.line_ids[1].product_id, self.product_2)
        self.assertEqual(invoice.line_ids[1].balance, -invoice_amounts[1])
        self.assertEqual(len(invoice.line_ids[1].matched_debit_ids), 0)
        self.assertEqual(len(invoice.line_ids[1].matched_credit_ids), 0)

        self.assertEqual(len(invoice.line_ids[2].matched_debit_ids), 0)
        self.assertEqual(len(invoice.line_ids[2].matched_credit_ids), len(payments))

        amount_residual = invoice.amount_total_signed
        for i, payment in enumerate(payments):
            amount_advance = advance_info[i]['amount'] * advance_info[i]['rate']

            self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].amount, min(amount_advance, amount_residual))
            self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].debit_move_id, invoice.line_ids[2])
            self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].debit_move_id.reconciled, paid)
            self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].amount, min(payment.amount_total, amount_residual))
            self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].credit_move_id, payment.line_ids[1])
            if payment.amount_total <= amount_residual:
                self.assertTrue(invoice.line_ids[2].matched_credit_ids[i].credit_move_id.reconciled)
                self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].credit_move_id.amount_residual, 0)
                self.assertEqual(invoice.line_ids[2].matched_credit_ids[i].credit_move_id.amount_residual_currency, 0)
            else:
                self.assertFalse(invoice.line_ids[2].matched_credit_ids[i].credit_move_id.reconciled)

            amount_residual -= amount_advance
