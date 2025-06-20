import datetime

from odoo import models, fields, _
from odoo.osv import expression


class MulticurrencyRevaluationReportCustomHandler(models.AbstractModel):
    _inherit = 'account.multicurrency.revaluation.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # fill the monetary items
        options['monetary_items'] = [
            {'id': 'asset_receivable', 'name': _("Receivable"), 'selected': True},
            {'id': 'liability_payable', 'name': _("Payable"), 'selected': True},
            {'id': 'bank_and_cash', 'name': _("Bank and Cash"), 'selected': True},
        ]

        if previous_options and previous_options.get('monetary_items'):
            previously_selected = {r['id'] for r in previous_options['monetary_items'] if r.get('selected')}
            for opt in options['monetary_items']:
                opt['selected'] = opt['id'] in previously_selected

        monetary_items_selected = [r for r in options['monetary_items'] if r['selected']]
        monetary_items_display_name = [r['name'] for r in monetary_items_selected]
        options['monetary_items_display_name'] = ', '.join(monetary_items_display_name)

        # get report date
        date_to = options['date']['date_to']
        date_to = fields.Date.from_string(date_to)
        date_to = datetime.datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, 999999)
        date_to = fields.Datetime.to_string(date_to)

        # update forced domain
        forced_domain = options.get('forced_domain') or []
        monetary_items_domains = []

        for monetary_item in monetary_items_selected:
            if monetary_item['id'] == 'asset_receivable':
                monetary_items_domains.append([
                    '|',
                        '&', '&',
                        '|', ('reconciled', '=', False), ('full_reconcile_id.create_date', '>', date_to),
                        ('account_id.account_type', '=', 'asset_receivable'),
                        ('debit', '!=', 0),
                        '&', '&',
                        ('move_id.currency_revaluation', '=', True),
                        ('account_id.account_type', '=', 'asset_receivable'),
                        ('credit', '!=', 0),
                ])
            elif monetary_item['id'] == 'liability_payable':
                monetary_items_domains.append([
                    '|',
                        '&', '&',
                        '|', ('reconciled', '=', False), ('full_reconcile_id.create_date', '>', date_to),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('credit', '!=', 0),
                        '&', '&',
                        ('move_id.currency_revaluation', '=', True),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('debit', '!=', 0),
                ])
            elif monetary_item['id'] == 'bank_and_cash':
                monetary_items_domains.append([('account_id.account_type', '=', 'asset_cash')])

        if monetary_items_domains:
            if len(monetary_items_domains) > 1:
                monetary_items_domains = expression.OR(monetary_items_domains)
            else:
                monetary_items_domains = monetary_items_domains[0]

        if forced_domain:
            options['forced_domain'] = expression.AND([monetary_items_domains, forced_domain])
        else:
            options['forced_domain'] = monetary_items_domains

    def _custom_line_postprocessor(self, report, options, lines):
        # firstly call super
        result = super()._custom_line_postprocessor(report, options, lines)

        # check all currency lines
        for line in result:
            res_model_name, res_id = report._get_model_info_from_id(line['id'])

            if res_model_name == 'res.currency':
                # and change currency rate display
                currency_info = options['currency_rates'][str(res_id)]
                line['name'] = '{for_cur} (1 {for_cur} = {rate:.4f} {comp_cur})'.format(
                    for_cur=currency_info['currency_name'],
                    comp_cur=self.env.company.currency_id.display_name,
                    rate=1.0 / (float(currency_info['rate']) or 1.0),
                )

        # return fixed result
        return result
