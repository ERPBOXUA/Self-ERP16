from odoo.addons.selferp_contract_settlement.models.account_move_line import ACCOUNT_TYPES_FOR_CONTRACT
from odoo.addons.selferp_l10n_ua_ext.tests.common import AccountTestCommon


class AccountContractTestCommon(AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Create contracts

        cls.contract_pa_1_s = cls.create_contract('Contract_pa_1_s', cls.partner_a, 'sale')
        cls.contract_pa_2_s = cls.create_contract('Contract_pa_2_s', cls.partner_a, 'sale')
        cls.contract_pa_3_s = cls.create_contract('Contract_pa_3_s', cls.partner_a, 'sale')

        cls.contract_pb_1_s = cls.create_contract('Contract_pb_1_s', cls.partner_b, 'sale')
        cls.contract_pb_2_s = cls.create_contract('Contract_pb_2_s', cls.partner_b, 'sale')
        cls.contract_pb_3_s = cls.create_contract('Contract_pb_3_s', cls.partner_b, 'sale')

        cls.contract_pa_1_p = cls.create_contract('Contract_pa_1_p', cls.partner_a, 'purchase')
        cls.contract_pa_2_p = cls.create_contract('Contract_pa_2_p', cls.partner_a, 'purchase')
        cls.contract_pa_3_p = cls.create_contract('Contract_pa_3_p', cls.partner_a, 'purchase')

        cls.contract_pb_1_p = cls.create_contract('Contract_pb_1_p', cls.partner_b, 'purchase')
        cls.contract_pb_2_p = cls.create_contract('Contract_pb_2_p', cls.partner_b, 'purchase')
        cls.contract_pb_3_p = cls.create_contract('Contract_pb_3_p', cls.partner_b, 'purchase')

    @classmethod
    def create_contract_invoice(cls, contract, partner, products, amounts, taxes=None, date=None, company=False):
        move = cls.create_invoice(partner, products, amounts, taxes, date, company)

        move.contract_id = contract

        return move

    def assert_contract_move_lines(self, lines, contract, more_than_zero=True, open_balance_contract=None):
        lines_count = 0
        open_balance_lines_count = 0
        for line in lines:
            if line.account_id.account_type in ACCOUNT_TYPES_FOR_CONTRACT:
                if open_balance_contract and not line.matched_debit_ids and not line.matched_credit_ids:
                    open_balance_lines_count += 1
                    self.assertEqual(open_balance_contract.id, line.contract_id.id, "Failed open balance contract value for move line")
                else:
                    lines_count += 1
                    self.assertEqual(contract.id, line.contract_id.id, "Failed contract value for move line")
            else:
                self.assertFalse(line.contract_id, "Contract should be None")
        if more_than_zero:
            self.assertGreater(lines_count, 0, "Should more than zero move lines with contract analytic")
        if open_balance_contract:
            self.assertGreater(open_balance_lines_count, 0, "Should more than zero move lines open balance")

    @classmethod
    def register_move(cls, contract, amount, invoice_date=None, override_move_date=False):
        if amount > 0:
            # create, confirm and deliver sale order
            sale_order = cls.create_sale_order(
                cls.partner_a,
                [cls.product_a],
                [1],
                [abs(amount)],
                contract=contract,
            )
            cls.confirm_sale_order(sale_order)
            cls.deliver_sale_order(sale_order)

            # create and confirm invoice
            invoice = cls.invoicing_sale_order(sale_order)
            cls.post_invoice(invoice, invoice_date=invoice_date)

            # return move lines
            return invoice.line_ids.filtered(lambda r: r.account_type == 'asset_receivable')

        else:
            # create, confirm and receive purchase order
            purchase_order = cls.create_purchase_order(
                cls.partner_a,
                [cls.product_a],
                [1],
                [abs(amount)],
                contract=contract,
            )
            cls.confirm_purchase_order(purchase_order)
            cls.receive_purchase_order(purchase_order)

            # create and confirm invoice
            invoice = cls.invoicing_purchase_order(purchase_order)
            cls.post_invoice(invoice, invoice_date=invoice_date)

            # a special fix for purchase order to get the correct date in move
            if invoice_date and override_move_date:
                invoice.date = invoice_date

            # return move lines
            return invoice.line_ids.filtered(lambda r: r.account_type == 'liability_payable')
