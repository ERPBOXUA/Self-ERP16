from odoo.tests import tagged

from .common import AccountContractTestCommon


@tagged('-at_install', 'post_install')
class TestPurchaseOrder(AccountContractTestCommon):

    def test_create_invoice_from_purchase_order(self):
        partner = self.partner_a
        contract = self.contract_pa_1_p
        purchase_order = self.create_purchase_order(
            partner=partner,
            products=[self.product_a],
            counts=[1],
            prices=[10],
            contract=contract,
        )

        self.confirm_purchase_order(purchase_order)

        self.receive_purchase_order(purchase_order)

        invoice = self.invoicing_purchase_order(purchase_order)
        self.assertEqual(contract.id, invoice.contract_id.id)
        self.assertGreater(len(invoice.line_ids), 0)
        self.assert_contract_move_lines(invoice.line_ids, contract)

        self.post_invoice(invoice)
        self.assert_contract_move_lines(invoice.line_ids, contract)

        st_line = self.create_bank_statement_line(
            partner=partner,
            amount=-invoice.amount_total,
        )

        self.validate_statement_line(st_line)
        self.assertEqual(invoice.payment_state, 'paid')

        st_move = st_line.move_id

        self.assert_contract_move_lines(st_move.line_ids, contract)

    def test_video_purchase_part2(self):
        partner = self.partner_a
        contract = self.contract_pa_1_p
        contract2 = self.contract_pa_2_p
        purchase_order = self.create_purchase_order(
            partner=partner,
            contract=contract,
            products=[self.product_a],
            counts=[1],
            prices=[10],
        )

        self.confirm_purchase_order(purchase_order)

        self.receive_purchase_order(purchase_order)

        invoice = self.invoicing_purchase_order(purchase_order)
        self.assertEqual(contract.id, invoice.contract_id.id)
        self.assertGreater(len(invoice.line_ids), 0)
        self.assert_contract_move_lines(invoice.line_ids, contract)

        self.post_invoice(invoice)
        self.assert_contract_move_lines(invoice.line_ids, contract)

        st_line = self.create_bank_statement_line(
            partner=partner,
            amount=-invoice.amount_total*1.2,
        )

        st_line.contract_id = contract2

        self.validate_statement_line(st_line)
        self.assertEqual(invoice.payment_state, 'paid')

        st_move = st_line.move_id

        self.assertFalse(st_move.contract_id)

        self.assert_contract_move_lines(st_move.line_ids, contract, open_balance_contract=contract2)
