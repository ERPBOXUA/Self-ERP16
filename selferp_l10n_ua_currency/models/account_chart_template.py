from odoo import models


def try_load_default_accounts(env, company):
    def _find_account(code):
        return env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)


    if not company.income_exchange_difference_account_id:
        company.income_exchange_difference_account_id = _find_account('711000')

    if not company.expense_exchange_difference_account_id:
        company.expense_exchange_difference_account_id = _find_account('942000')

    if not company.bank_commission_account_id:
        company.bank_commission_account_id = _find_account('920000')

    if not company.transit_in_national_currency_account_id:
        company.transit_in_national_currency_account_id = _find_account('333000')

    if not company.transit_in_foreign_currency_account_id:
        company.transit_in_foreign_currency_account_id = _find_account('334000')


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):

        ret = super()._load(company)

        if self.env.ref('l10n_ua.l10n_ua_psbo_chart_template').id == self.id:
            try_load_default_accounts(self.env, company)

        return ret
