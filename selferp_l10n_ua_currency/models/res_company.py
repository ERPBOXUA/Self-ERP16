import datetime
import json
import requests
import requests.adapters

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    income_exchange_difference_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Gain from FX difference",
        check_company=True,
    )
    expense_exchange_difference_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Loss from FX difference",
        check_company=True,
    )
    bank_commission_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Bank commission account",
        check_company=True,
    )
    transit_in_national_currency_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Transit account in national currency",
        check_company=True,
    )
    transit_in_foreign_currency_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Transit account in foreign currency",
        check_company=True,
    )

    currency_provider = fields.Selection(
        selection_add=[('nbu', "National Bank of Ukraine")],
        ondelete={'nbu': 'set null'},
    )

    def _parse_nbu_data(self, available_currencies):
        request_url = 'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json'
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()

        rates_dict = {}
        available_currency_names = available_currencies.mapped('name')
        data = json.loads(response.content)
        for child_node in data:
            currency_code = child_node['cc'].upper()
            if currency_code in available_currency_names:
                rate = 1 / child_node['rate']
                date_rate = datetime.datetime.strptime(child_node['exchangedate'], '%d.%m.%Y').date()
                rates_dict[currency_code] = (rate, date_rate)

        if 'UAH' in available_currency_names:
            rates_dict['UAH'] = (1.0, datetime.datetime.strptime(data[0]['exchangedate'], '%d.%m.%Y').date())

        return rates_dict

    def _compute_currency_provider(self):
        non_ukraine = self.browse()
        for record in self:
            if record.country_id.code == 'UA' or (record.currency_id and record.currency_id.name == 'UAH'):
                record.currency_provider = 'nbu'
            else:
                non_ukraine += record
        if non_ukraine:
            super(ResCompany, non_ukraine)._compute_currency_provider()
