from odoo import models


def try_load_default_accounts(env, company):
    def _find_account(code):
        return env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)

    if not company.income_currency_exchange_account_id:
        company.income_currency_exchange_account_id = _find_account('714000')

    if not company.expense_currency_exchange_account_id:
        company.expense_currency_exchange_account_id = _find_account('945000')


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super()._load(company)

        if self.env.ref('l10n_ua.l10n_ua_psbo_chart_template').id == self.id:
            try_load_default_accounts(self.env, company)

        return res
