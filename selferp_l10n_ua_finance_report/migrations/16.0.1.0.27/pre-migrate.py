from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_finance_report.hooks import _delete_report


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _delete_report(env, 'selferp_l10n_ua_finance_report.account_report_l10n_ua_financial_results_2')
    _delete_report(env, 'selferp_l10n_ua_finance_report.account_report_l10n_ua_balance_sheet_1')
