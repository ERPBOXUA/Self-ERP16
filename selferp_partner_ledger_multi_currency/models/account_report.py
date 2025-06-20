from odoo import models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _add_totals_below_sections(self, lines, options):
        # switch off total line for partner when it's Partner Ledger Multi Currency report
        if (
            lines
            and not options.get('ignore_totals_below_sections')
            and self == self.env.ref('selferp_partner_ledger_multi_currency.account_report_partner_ledger_multi_currency')
        ):
            model, record_id = self._get_model_info_from_id(lines[0]['id'])
            if model == 'res.partner':
                options = dict(options, ignore_totals_below_sections=True)

        # call super
        return super()._add_totals_below_sections(lines, options)
