from odoo.tests import tagged

from .common import AccountContractTestCommon


@tagged('-at_install', 'post_install')
class TestBankStatementLine(AccountContractTestCommon):

    def test_bank_statement_line(self):
        statement_line = self.create_contract_bank_statement_line(
            partner=self.partner_a,
            amount=10,
            contract=self.contract_pa_1_p,
        )

        move = self.validate_statement_line(statement_line)

        self.assert_contract_move_lines(lines=move.line_ids, contract=self.contract_pa_1_p)
