from odoo import models, fields, _
from odoo.osv import expression


class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_accounts = fields.Boolean(
        string="Accounts",
        default=False,
    )

    def _init_options_account_type(self, options, previous_options=None):
        super()._init_options_account_type(options, previous_options=previous_options)

        # add custom per report
        if self.filter_accounts:
            # add filter by accounts
            previous_account_ids = previous_options and previous_options.get('account_ids') or []
            selected_account_ids = [int(account_id) for account_id in previous_account_ids]

            # search instead of browse so that record rules apply and filter out the ones the user does not have access to
            selected_accounts = selected_account_ids and self.env['account.account'].search([('id', 'in', selected_account_ids)]) or self.env['account.account']
            options.update({
                'filter_accounts': True,
                'account_ids': selected_accounts.ids,
                'selected_account_ids': selected_accounts.mapped('name'),
            })

    def _get_options_domain(self, options, date_scope):
        # get original domain by options
        domain = super()._get_options_domain(options, date_scope)

        # add custom per report
        if self.filter_accounts:
            # check selected accounts
            if options.get('account_ids'):
                account_ids = [int(account_id) for account_id in options['account_ids']]
                custom_domain = [('account_id', 'in', account_ids)]

                # concatenate domains
                domain = expression.AND([custom_domain, domain])

        # return resulting domain
        return domain
