from odoo.tests import tagged

from .common import AccountContractTestCommon


@tagged('-at_install', 'post_install')
class TestSaleOrder(AccountContractTestCommon):

    def test_create_invoice_from_sale_order(self):
        contract = self.contract_pa_1_s
        sale = self.create_sale_order(
            partner=self.partner_a,
            products=[self.product_a],
            counts=[1],
            prices=[1],
            contract=contract,
        )
        self.confirm_sale_order(sale)

        invoice = self.invoicing_sale_order(sale)

        self.assertEqual(contract.id, invoice.contract_id.id)

        self.assertGreater(len(invoice.line_ids), 0)

        self.assert_contract_move_lines(invoice.line_ids, contract=contract)
