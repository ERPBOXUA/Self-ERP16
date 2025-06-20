from collections import defaultdict

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        # do post
        to_post = super()._post(soft=soft)

        for record in to_post:
            # check existing debit and credit records by same account
            accounts = defaultdict(lambda: record.line_ids.browse())
            for line in record.line_ids:
                if line.account_type == 'liability_payable':
                    accounts[line.account_id] += line

            # check single
            account_to_reconcile = None
            for account, lines in accounts.items():
                if len(lines) > 1 and lines.filtered(lambda r: not record.currency_id.is_zero(r.debit)) and lines.filtered(lambda r: not record.currency_id.is_zero(r.credit)):
                    if account_to_reconcile:
                        # if already exists - just skip reconcile at all
                        account_to_reconcile = None
                        break
                    account_to_reconcile = account

            # reconcile lines
            if account_to_reconcile:
                accounts[account_to_reconcile].with_context(reduced_line_sorting=True).reconcile()

        # return result
        return to_post
