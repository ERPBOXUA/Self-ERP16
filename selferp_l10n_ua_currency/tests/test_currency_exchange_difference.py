from odoo.tests import tagged

from .common import TestCurrencyCommon


@tagged('post_install', '-at_install')
class TestCurrencyExchangeDifference(TestCurrencyCommon):

    def test_currency_exchange_unreconcile(self):
        # create invoice with currency rate = 41.0
        invoice = self.init_invoice(
            'out_invoice',
            company=self.company,
            invoice_date=self.invoice_date,
            partner=self.partner,
            products=[self.product],
            amounts=[1000.00],
            taxes=[],
            currency=self.currency_usd,
            post=True,
        )

        # pay invoice with currency rate - 39.0
        payment = self.pay_invoice(invoice)

        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.amount_total_in_currency_signed, 1000.0)
        self.assertEqual(payment.currency_id, self.currency_usd)
        self.assertEqual(payment.amount_total_signed, 39000.0)
        self.assertEqual(payment.state, 'posted')

        self.assertEqual(invoice.amount_residual, 0)
        self.assertEqual(invoice.payment_state, 'in_payment')       # not 'paid' until reconciling with a bank statement
        self.assertEqual(len(invoice.line_ids), 2)

        # check currency exchange difference
        invoice_line = invoice.line_ids.filtered(lambda r: r.balance == 41000.0)
        self.assertEqual(len(invoice_line), 1)
        self.assertEqual(len(invoice_line.matched_debit_ids), 0)
        self.assertEqual(len(invoice_line.matched_credit_ids), 2)
        self.assertEqual(invoice_line.matched_credit_ids[0].amount, 39000.0)
        self.assertEqual(invoice_line.matched_credit_ids[0].debit_move_id, invoice_line)
        self.assertEqual(invoice_line.matched_credit_ids[0].credit_move_id.payment_id, payment)
        self.assertEqual(invoice_line.matched_credit_ids[0].credit_move_id, payment.line_ids[1])
        self.assertEqual(invoice_line.matched_credit_ids[1].amount, 2000.0)
        self.assertEqual(invoice_line.matched_credit_ids[1].debit_move_id, invoice_line)
        self.assertEqual(invoice_line.matched_credit_ids[1].credit_move_id.balance, -2000.0)
        self.assertEqual(invoice_line.matched_credit_ids[1].credit_move_id.move_id.line_ids[1].account_id, invoice.company_id.expense_exchange_difference_account_id)
        self.assertEqual(len(invoice_line.matched_credit_ids[1].credit_move_id.matched_debit_ids), 1)
        self.assertEqual(len(invoice_line.matched_credit_ids[1].credit_move_id.matched_credit_ids), 0)
        self.assertEqual(invoice_line.matched_credit_ids[1].credit_move_id.matched_debit_ids[0].amount, 2000.0)
        self.assertEqual(invoice_line.matched_credit_ids[1].credit_move_id.matched_debit_ids[0].debit_move_id, invoice_line)

        full_reconcile = invoice_line.matched_credit_ids.mapped('full_reconcile_id')
        self.assertEqual(len(full_reconcile), 1)
        self.assertEqual(len(full_reconcile.partial_reconcile_ids), 2)      # 2 partial reconciles: payment + invoice; exchange_diff + invoice
        self.assertEqual(len(full_reconcile.reconciled_line_ids), 3)        # 3 lines: invoice + payment + exchange_diff

        exchange_diff_move = invoice_line.matched_credit_ids[1].credit_move_id.move_id

        # unreconcile currency exchange difference
        invoice.js_remove_outstanding_partial(invoice_line.matched_credit_ids[0].id)

        # check currency exchange difference records removed (not storned)
        self.assertFalse(exchange_diff_move.exists())

        self.assertEqual(invoice.amount_residual, 1000.0)
        self.assertEqual(invoice.amount_residual_signed, 41000.0)
        self.assertEqual(invoice.payment_state, 'not_paid')
        self.assertEqual(len(invoice.line_ids), 2)
