from datetime import date

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo.addons.selferp_l10n_ua_ext.tests.common import AccountTestCommon


@tagged('post_install', '-at_install')
class TestRevaluationZeroBalance(TestAccountReportsCommon, AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_eur = cls.env.ref('base.EUR')
        cls.currency_eur.action_unarchive()

        cls.currency_uah = cls.env.ref('base.UAH')
        cls.currency_uah.action_unarchive()

        cls.company = cls.setup_company_data('Test Company', currency_id=cls.currency_uah.id)['company']
        cls.env.company = cls.company
        cls.env.user.write({
            'company_id': cls.company.id,
        })

        cls.pricelist_eur = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist EUR',
            'currency_id': cls.currency_eur.id,
        })
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Test Partner 1',
            'property_product_pricelist': cls.pricelist_eur.id,
        })
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Test Partner 2',
            'property_product_pricelist': cls.pricelist_eur.id,
        })

        cls.bank_journal = cls.env['account.journal'].search(
            [
                ('company_id', '=', cls.company.id),
                ('type', '=', 'bank'),
            ],
            limit=1,
        )
        cls.bank_journal.currency_id = cls.currency_eur

        cls.env['res.currency.rate'].create([
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 15),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 38.9392,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 17),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 39.3054,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 12, 13),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 39.9376,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 12, 19),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 40.5918,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 12, 28),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 41.3611,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 12, 31),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 41.1538,
            },
            {
                'company_id': cls.company.id,
                'name': date(2024, 1, 1),
                'currency_id': cls.currency_eur.id,
                'inverse_company_rate': 41.0042,
            },
        ])

    def test_revaluation_zero_balance(self):
        """ Skip stornation of records with zero balances in currency on
            revaluation - it's should be currency exchange difference only.

            See details:
                https://docs.google.com/spreadsheets/d/1V8YFUWuxWfQkxC4ETnNKKWMoNGEZUwhzf8XIBHtWmss/edit#gid=505797015
                https://www.self-erp.com/web#id=2801&cids=1&model=project.task&view_type=form
        """
        company_currency = self.company.currency_id

        def _create_and_check_sale(date_inv, amount_invoice, date_payment, amount_payment, amount_diff):
            # create, confirm and deliver sale order
            sale_order = self.create_sale_order(
                self.partner_1,
                [self.product_a],
                [1],
                [780],
                date_order=date_inv,
                currency=self.currency_eur,
            )
            self.confirm_sale_order(sale_order)
            self.deliver_sale_order(sale_order)

            # create and confirm invoice
            invoice = self.invoicing_sale_order(sale_order)
            self.post_invoice(invoice, invoice_date=date_inv)

            self.assertEqual(len(invoice.line_ids), 2)
            self.assertEqual(invoice.line_ids[0].balance, -amount_invoice)
            self.assertFalse(invoice.line_ids[0].reconciled)
            self.assertEqual(len(invoice.line_ids[0].matched_debit_ids), 0)
            self.assertEqual(len(invoice.line_ids[0].matched_credit_ids), 0)
            self.assertEqual(invoice.line_ids[1].balance, amount_invoice)
            self.assertFalse(invoice.line_ids[1].reconciled)
            self.assertEqual(len(invoice.line_ids[1].matched_debit_ids), 0)
            self.assertEqual(len(invoice.line_ids[1].matched_credit_ids), 0)

            # create bank statement line
            statement_line = self.create_bank_statement_line(
                self.partner_1,
                780,
                date=date_payment,
            )
            self.assertEqual(company_currency.compare_amounts(statement_line.amount_total_signed, amount_payment), 0)
            self.assertEqual(len(statement_line.line_ids), 2)
            self.assertEqual(company_currency.compare_amounts(statement_line.line_ids[0].balance, amount_payment), 0)
            self.assertFalse(statement_line.line_ids[0].reconciled)
            self.assertEqual(len(statement_line.line_ids[0].matched_debit_ids), 0)
            self.assertEqual(len(statement_line.line_ids[0].matched_credit_ids), 0)
            self.assertEqual(company_currency.compare_amounts(statement_line.line_ids[1].balance, -amount_payment), 0)
            self.assertFalse(statement_line.line_ids[1].reconciled)
            self.assertEqual(len(statement_line.line_ids[1].matched_debit_ids), 0)
            self.assertEqual(len(statement_line.line_ids[1].matched_credit_ids), 0)

            # validate statement line
            self.validate_statement_line(statement_line)

            # check reconciliation result
            self.assertEqual(len(invoice.line_ids[0].matched_debit_ids), 0)
            self.assertEqual(len(invoice.line_ids[0].matched_credit_ids), 0)
            self.assertEqual(len(invoice.line_ids[1].matched_debit_ids), 0)
            self.assertEqual(len(invoice.line_ids[1].matched_credit_ids), 1)
            self.assertTrue(invoice.line_ids[1].reconciled)
            self.assertEqual(company_currency.compare_amounts(invoice.line_ids[1].matched_credit_ids[0].amount, amount_invoice), 0)
            self.assertEqual(invoice.line_ids[1].matched_credit_ids[0].credit_move_id, statement_line.line_ids[1])

            self.assertEqual(len(statement_line.line_ids[0].matched_debit_ids), 0)
            self.assertEqual(len(statement_line.line_ids[0].matched_credit_ids), 0)
            self.assertTrue(statement_line.line_ids[1].reconciled)
            self.assertEqual(len(statement_line.line_ids[1].matched_debit_ids), 2)
            self.assertEqual(len(statement_line.line_ids[1].matched_credit_ids), 0)
            self.assertEqual(company_currency.compare_amounts(amount_payment - amount_invoice, amount_diff), 0)    # Exchange difference
            self.assertEqual(company_currency.compare_amounts(statement_line.line_ids[1].matched_debit_ids[0].amount, amount_diff), 0)
            self.assertNotEqual(statement_line.line_ids[1].matched_debit_ids[0].debit_move_id, statement_line.line_ids[1])
            self.assertTrue(statement_line.line_ids[1].matched_debit_ids[0].debit_move_id.reconciled)
            self.assertEqual(statement_line.line_ids[1].matched_debit_ids[1].amount, amount_invoice)
            self.assertEqual(statement_line.line_ids[1].matched_debit_ids[1].debit_move_id, invoice.line_ids[1])

            return sale_order, invoice, statement_line

        #
        # First sale
        #
        sale_order1, invoice1, statement_line1 = _create_and_check_sale(
            date(2023, 11, 15),
            30372.58,
            date(2023, 11, 17),
            30658.21,
            285.63,
        )

        #
        # Second sale
        #
        sale_order2, invoice2, statement_line2 = _create_and_check_sale(
            date(2023, 12, 13),
            31151.33,
            date(2023, 12, 19),
            31661.60,
            510.27,
        )

        #
        # create advance bank statement line
        #
        statement_line_advance = self.create_bank_statement_line(
            self.partner_1,
            -1560,
            date=date(2023, 12, 21),
        )
        self.assertEqual(statement_line_advance.amount_total_signed, 63323.21)
        self.assertEqual(len(statement_line_advance.line_ids), 2)
        self.assertEqual(statement_line_advance.line_ids[0].balance, -63323.21)
        self.assertFalse(statement_line_advance.line_ids[0].reconciled)
        self.assertEqual(len(statement_line_advance.line_ids[0].matched_debit_ids), 0)
        self.assertEqual(len(statement_line_advance.line_ids[0].matched_credit_ids), 0)
        self.assertEqual(statement_line_advance.line_ids[1].balance, 63323.21)
        self.assertFalse(statement_line_advance.line_ids[1].reconciled)
        self.assertEqual(len(statement_line_advance.line_ids[1].matched_debit_ids), 0)
        self.assertEqual(len(statement_line_advance.line_ids[1].matched_credit_ids), 0)

        #
        # create purchase order with another partner
        #
        purchase_order = self.create_purchase_order(
            self.partner_2,
            [self.product_a],
            [1],
            [650],
            date=date(2023, 12, 29),
            currency=self.currency_eur,
        )
        self.confirm_and_receive_purchase_order(purchase_order)
        purchase_invoice = self.invoicing_purchase_order(purchase_order)
        self.post_invoice(purchase_invoice, invoice_date=date(2023, 12, 29))

        amount_purchase_invoice = 26884.72
        self.assertEqual(len(purchase_invoice.line_ids), 2)
        self.assertEqual(purchase_invoice.line_ids[0].balance, amount_purchase_invoice)
        self.assertFalse(purchase_invoice.line_ids[0].reconciled)
        self.assertEqual(len(purchase_invoice.line_ids[0].matched_debit_ids), 0)
        self.assertEqual(len(purchase_invoice.line_ids[0].matched_credit_ids), 0)
        self.assertEqual(purchase_invoice.line_ids[1].balance, -amount_purchase_invoice)
        self.assertFalse(purchase_invoice.line_ids[1].reconciled)
        self.assertEqual(len(purchase_invoice.line_ids[1].matched_debit_ids), 0)
        self.assertEqual(len(purchase_invoice.line_ids[1].matched_credit_ids), 0)

        #
        # get and execute a report
        #
        report = self.env.ref('account_reports.multicurrency_revaluation_report').with_context(lang='en_US')
        options = self._generate_options(
            report,
            False,
            fields.Date.from_string('2023-12-31'),
        )
        options['unfold_all'] = True
        lines = report._get_lines(options)

        self.assertEqual(len(lines), 11)

        # 1) 'Accounts To Adjust' header
        self.assertFalse(lines[0]['unfoldable'])
        self.assertTrue(lines[0]['unfolded'])
        # 2) group by currency
        self.assertFalse(lines[1]['unfoldable'])
        self.assertTrue(lines[1]['unfolded'])
        # 3) group by account '311004 Bank'
        self.assertTrue(lines[2]['unfoldable'])
        self.assertTrue(lines[2]['unfolded'])

        # 4) move line 1
        self.assertEqual(lines[3]['caret_options'], 'account.move.line')
        self.assertTrue(lines[3]['name'].startswith(statement_line_advance.name))
        self.assertEqual(lines[3]['columns'][1]['no_format'], -63323.21)

        # 5) move line 2
        self.assertEqual(lines[4]['caret_options'], 'account.move.line')
        self.assertTrue(lines[4]['name'].startswith(statement_line2.name))
        self.assertEqual(lines[4]['columns'][1]['no_format'], 31661.60)

        # 6) move line 3
        self.assertEqual(lines[5]['caret_options'], 'account.move.line')
        self.assertTrue(lines[5]['name'].startswith(statement_line1.name))
        self.assertEqual(lines[5]['columns'][1]['no_format'], 30658.21)

        # 7) total by account
        self.assertFalse(lines[6]['unfoldable'])
        self.assertFalse(lines[6]['unfolded'])
        self.assertEqual(lines[6]['columns'][1]['no_format'], -1003.40)
        self.assertEqual(lines[6]['columns'][2]['no_format'], 0)
        self.assertEqual(lines[6]['columns'][3]['no_format'], 1003.40)

        # 8) group by account '631000 Розрахунки з вітчизняними постачальниками'
        self.assertTrue(lines[7]['unfoldable'])
        self.assertTrue(lines[7]['unfolded'])

        # 9) move line
        self.assertEqual(lines[8]['caret_options'], 'account.move.line')
        self.assertTrue(lines[8]['name'].startswith(purchase_invoice.name))
        self.assertEqual(lines[8]['columns'][1]['no_format'], -amount_purchase_invoice)

        # 10) total by account
        self.assertFalse(lines[9]['unfoldable'])
        self.assertFalse(lines[9]['unfolded'])
        self.assertEqual(company_currency.compare_amounts(lines[9]['columns'][1]['no_format'], -amount_purchase_invoice), 0)
        self.assertEqual(company_currency.compare_amounts(lines[9]['columns'][2]['no_format'], -26749.97), 0)
        self.assertEqual(company_currency.compare_amounts(lines[9]['columns'][3]['no_format'], 134.75), 0)

        # 11) total by currency
        self.assertFalse(lines[10]['unfoldable'])
        self.assertFalse(lines[10]['unfolded'])
        self.assertEqual(company_currency.compare_amounts(lines[10]['columns'][1]['no_format'], (-1003.40) + (-amount_purchase_invoice)), 0)
        self.assertEqual(company_currency.compare_amounts(lines[10]['columns'][2]['no_format'], 0 - 26749.97), 0)
        self.assertEqual(company_currency.compare_amounts(lines[10]['columns'][3]['no_format'], 1003.40 + 134.75), 0)

        #
        # Revaluate currency
        #
        wizard = self.env['account.multicurrency.revaluation.wizard'].with_context(multicurrency_revaluation_report_options=options).create({})
        action = wizard.create_entries()

        # get adjustment move
        adjustment_move = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(len(adjustment_move.line_ids), 4)
        self.assertEqual(adjustment_move.line_ids[0].balance, 1003.40)
        self.assertEqual(adjustment_move.line_ids[1].balance, -1003.40)
        self.assertEqual(adjustment_move.line_ids[2].balance, 134.75)
        self.assertEqual(adjustment_move.line_ids[3].balance, -134.75)

        # and there is a reversal move, but without 2 lines
        # because the currency amount is 0 (it's just exchange difference)
        self.assertFalse(not adjustment_move.reversal_move_id)
        self.assertEqual(len(adjustment_move.reversal_move_id.line_ids), 2)
        self.assertEqual(adjustment_move.reversal_move_id.line_ids[0].balance, -134.75)
        self.assertEqual(adjustment_move.reversal_move_id.line_ids[1].balance, 134.75)
