from odoo.tests import tagged

from .common import AccountContractTestCommon


@tagged('-at_install', 'post_install')
class TestCreditNote(AccountContractTestCommon):

    def test_credit_note(self):
        move = self.create_contract_invoice(
            partner=self.partner_a,
            products=[self.product_a],
            amounts=[1],
            contract=self.contract_pa_1_s
        )

        self.post_invoice(move)

        self.pay_invoice(move)

        refund = self.refund_invoice(move)

        self.assert_contract_move_lines(lines=refund.line_ids, contract=self.contract_pa_1_s)
