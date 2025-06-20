from odoo import models, fields, api


ACCOUNT_TYPES_FOR_CONTRACT = [
    'asset_receivable',
    'liability_payable',
]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        compute='_compute_contract_id',
        store=True,
        index=True,
    )

    @api.depends('move_id.contract_id', 'account_id', 'statement_line_id', 'matched_debit_ids', 'matched_credit_ids')
    @api.onchange('move_id', 'account_id', 'statement_line_id', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_contract_id(self):
        for line in self:
            contract_id = None

            if line.account_id.account_type in ACCOUNT_TYPES_FOR_CONTRACT:
                if line.move_id and line.move_id.contract_id:
                    contract_id = line.move_id.contract_id

                # get contract from matched line
                if not contract_id and line.matched_debit_ids and len(line.matched_debit_ids) == 1:
                    contract_id = (
                        line.matched_debit_ids[0].debit_move_id.contract_id or
                        line.matched_debit_ids[0].debit_move_id.move_id.contract_id
                    )

                # get contract from matched line
                if not contract_id and line.matched_credit_ids and len(line.matched_credit_ids) == 1:
                    contract_id = (
                        line.matched_credit_ids[0].credit_move_id.contract_id or
                        line.matched_credit_ids[0].credit_move_id.move_id.contract_id
                    )

                # get contract from statement line
                if not contract_id and line.statement_line_id and line.statement_line_id.contract_id:
                    contract_id = line.statement_line_id.contract_id

            line.contract_id = contract_id

    def _is_contract_open_balance(self):
        return self.contract_id and not self.matched_credit_ids and not self.matched_debit_ids

    def reconcile(self):
        res = super().reconcile()
        self._compute_contract_id()
        return res
