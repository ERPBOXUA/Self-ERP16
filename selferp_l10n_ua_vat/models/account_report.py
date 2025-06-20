from odoo import models
from odoo.osv import expression


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_options_domain(self, options, date_scope):
        # get original domain by options
        domain = super()._get_options_domain(options, date_scope)

        # add custom domain per report
        if self.env.ref('selferp_l10n_ua_vat.account_report_vat_first_event') in self:
            custom_domain = [
                ('account_id.first_event', '=', True),
                ('account_id.account_type', '=', options['partner_account_type']),
            ]

            if options['tracking_first_event'] != 'all':
                if options['partner_account_type'] == 'asset_receivable':
                    custom_domain.append(('partner_id.tracking_first_event', '=', options['tracking_first_event']))
                elif options['partner_account_type'] == 'liability_payable':
                    custom_domain.append(('partner_id.tracking_first_event_vendor', '=', options['tracking_first_event']))

            # concatenate domains
            domain = expression.AND([custom_domain, domain])

        # return resulting domain
        return domain
