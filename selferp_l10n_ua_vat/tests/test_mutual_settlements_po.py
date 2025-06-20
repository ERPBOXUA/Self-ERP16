from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.selferp_contract_settlement.tests.common import AccountTestCommon


@tagged('-at_install', 'post_install')
class TestMutualSettlements(AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency = cls.company_data['currency']

        cls.contract_pa_1_p = cls.create_contract('Contract_pa_1_p', cls.partner_a, 'purchase')

    def test_reconcile_with_order(self):
        order1, invoice, invoice_move_line = self._create_order_and_invoice()

        #
        # check reconcile with Open Balance
        #
        statement_line1 = self.create_contract_bank_statement_line(
            partner=self.partner_a,
            amount=-10.5,
            contract=self.contract_pa_1_p,
            purchase_order=order1,
        )

        # reconcile bank statement line with Open Balance
        bank_move1 = self.validate_statement_line(
            statement_line1,
            remove_new_amls=True,
        )

        # check sale order in a move line
        move_line1 = bank_move1.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
        self.assertEqual(len(move_line1), 1)
        self.assertEqual(move_line1.linked_purchase_order_id, order1)

        # check order move lines
        self.assertNotEqual(move_line1, invoice_move_line)
        self.assertEqual(order1.move_line_count, 2)
        self.assertTrue(invoice_move_line in order1.move_line_ids)
        self.assertTrue(move_line1 in order1.move_line_ids)

        # check payment widget
        self.assertTrue(not invoice.invoice_payments_widget)
        to_reconcile = invoice.invoice_outstanding_credits_debits_widget
        self.assertFalse(not to_reconcile)
        self.assertFalse(not to_reconcile.get('content'))
        self.assertEqual(len(to_reconcile.get('content')), 1)
        self.assertEqual(to_reconcile.get('content')[0].get('id'), move_line1.id)
        self.assertEqual(float_compare(to_reconcile.get('content')[0].get('amount'), move_line1.debit, precision_digits=self.currency.decimal_places), 0)

        #
        # check reconcile with invoice line
        # (set amount less than invoice amount)
        #
        order2 = self.create_purchase_order(
            self.partner_a,
            [self.product_a,    self.product_b],
            [1,                 2],
            [20.00,             10.00],
        )

        statement_line2 = self.create_contract_bank_statement_line(
            partner=self.partner_a,
            amount=-22.44,
            purchase_order=order2,
        )

        # reconcile bank statement line
        bank_move2 = self.validate_statement_line(statement_line2)

        # check sale order in a move line
        move_line2 = bank_move2.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
        self.assertEqual(len(move_line2), 1)
        self.assertEqual(move_line2.linked_purchase_order_id, order1)

        # check order move lines
        self.assertNotEqual(move_line2, invoice_move_line)
        self.assertFalse(not move_line2.matched_credit_ids)
        self.assertEqual(len(move_line2.matched_credit_ids), 1)
        self.assertEqual(move_line2.matched_credit_ids.credit_move_id, invoice_move_line)
        self.assertEqual(order1.move_line_count, 3)
        self.assertTrue(invoice_move_line in order1.move_line_ids)
        self.assertTrue(move_line1 in order1.move_line_ids)
        self.assertTrue(move_line2 in order1.move_line_ids)

        # check payment widget
        reconciled = invoice.invoice_payments_widget
        self.assertFalse(not reconciled)
        self.assertFalse(not reconciled.get('content'))
        self.assertEqual(len(reconciled.get('content')), 1)
        self.assertEqual(float_compare(reconciled.get('content')[0].get('amount'), move_line2.debit, precision_digits=self.currency.decimal_places), 0)
        to_reconcile = invoice.invoice_outstanding_credits_debits_widget
        self.assertFalse(not to_reconcile)
        self.assertFalse(not to_reconcile.get('content'))
        self.assertEqual(len(to_reconcile.get('content')), 1)
        self.assertEqual(to_reconcile.get('content')[0].get('id'), move_line1.id)
        self.assertEqual(float_compare(to_reconcile.get('content')[0].get('amount'), move_line1.debit, precision_digits=self.currency.decimal_places), 0)

        #
        # check invoice line and Open Balance
        # (set amount greater than invoice amount)
        #
        statement_line3 = self.create_contract_bank_statement_line(
            partner=self.partner_a,
            amount=-1 * (invoice_move_line.amount_currency + 1000),
            purchase_order=order2,
        )

        # reconcile bank statement line
        bank_move3 = self.validate_statement_line(statement_line3)

        # check sale order in a move line
        move_line3 = bank_move3.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
        self.assertEqual(len(move_line3), 2)
        self.assertEqual(move_line3[0].linked_purchase_order_id, order1)
        self.assertEqual(move_line3[1].linked_purchase_order_id, order2)

        # check order move lines
        self.assertNotEqual(move_line3[0], invoice_move_line)
        self.assertNotEqual(move_line3[1], invoice_move_line)
        self.assertFalse(not move_line3[0].matched_credit_ids)
        self.assertEqual(len(move_line3[0].matched_credit_ids), 1)
        self.assertEqual(move_line3[0].matched_credit_ids.credit_move_id, invoice_move_line)
        self.assertEqual(order1.move_line_count, 4)
        self.assertTrue(invoice_move_line in order1.move_line_ids)
        self.assertTrue(move_line1 in order1.move_line_ids)
        self.assertTrue(move_line2 in order1.move_line_ids)
        self.assertTrue(move_line3[0] in order1.move_line_ids)
        self.assertTrue(move_line3[1] not in order1.move_line_ids)

        self.assertEqual(order2.move_line_count, 1)
        self.assertEqual(len(order2.move_line_ids), 1)
        self.assertTrue(move_line3[1] in order2.move_line_ids)

        # check payment widget
        reconciled = invoice.invoice_payments_widget
        self.assertFalse(not reconciled)
        self.assertFalse(not reconciled.get('content'))
        self.assertEqual(len(reconciled.get('content')), 2)
        self.assertEqual(reconciled.get('content')[0].get('move_id'), move_line2.move_id.id)
        self.assertEqual(float_compare(reconciled.get('content')[0].get('amount'), move_line2.debit, precision_digits=self.currency.decimal_places), 0)
        self.assertEqual(reconciled.get('content')[1].get('move_id'), move_line3[0].move_id.id)
        self.assertEqual(float_compare(reconciled.get('content')[1].get('amount'), move_line3[0].debit, precision_digits=self.currency.decimal_places), 0)
        to_reconcile = invoice.invoice_outstanding_credits_debits_widget
        self.assertTrue(not to_reconcile)

        #
        # check actions
        #
        self._check_order_action(order1)
        self._check_order_action(order2)

    def test_create_payment(self):
        order, invoice, invoice_move_line = self._create_order_and_invoice()

        # create wizard and confirm payment
        wizard = self.env['account.payment.register'].with_context(
            active_model=invoice._name,
            active_ids=invoice.ids,
        ).create({
            'amount': 33.00,
        })
        action = wizard.action_create_payments()
        self.assertFalse(not action)

        # get payment
        payment_id = action.get('res_id')
        self.assertFalse(not payment_id)

        payment = self.env['account.payment'].browse(payment_id).exists()
        self.assertFalse(not payment)

        # check move lines
        self.assertEqual(len(payment.line_ids), 2)

        payment_move_line = payment.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
        self.assertEqual(len(payment_move_line), 1)
        self.assertNotEqual(payment_move_line, invoice_move_line)

        self.assertEqual(payment_move_line.linked_sale_order_id, invoice_move_line.linked_sale_order_id)

    def _create_order_and_invoice(self):
        # create, confirm and receive purchase order
        order = self.create_purchase_order(
            self.partner_a,
            [self.product_a, self.product_b],
            [2, 3],
            [123.45, 10.00],
        )
        self.confirm_purchase_order(order)
        self.receive_purchase_order(order)

        # create and confirm invoice
        invoice = self.invoicing_purchase_order(order)
        self.post_invoice(invoice)

        # all sale order lines merged into one receivable move line
        invoice_move_line = invoice.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
        self.assertEqual(len(invoice_move_line), 1)
        self.assertEqual(invoice_move_line.linked_purchase_order_id, order)
        for line in (invoice.line_ids - invoice_move_line):
            self.assertTrue(not line.linked_purchase_order_id)

        # check order move lines
        self.assertEqual(order.move_line_count, 1)
        self.assertEqual(len(order.move_line_ids), order.move_line_count)
        self.assertEqual(order.move_line_ids[0], invoice_move_line)

        # check payment widget
        self.assertTrue(not invoice.invoice_payments_widget)
        self.assertTrue(not invoice.invoice_outstanding_credits_debits_widget)

        return order, invoice, invoice_move_line

    def _check_order_action(self, order):
        action = order.action_view_journal_items()

        self.assertIsNotNone(action)

        AccountMoveLine = self.env['account.move.line']
        self.assertEqual(action.get('res_model'), AccountMoveLine._name)

        move_lines_domain = action.get('domain')
        self.assertIsNotNone(move_lines_domain)

        move_lines = AccountMoveLine.search(move_lines_domain)
        self.assertEqual(len(move_lines), order.move_line_count)
        self.assertListEqual(move_lines.ids, order.move_line_ids.ids)

