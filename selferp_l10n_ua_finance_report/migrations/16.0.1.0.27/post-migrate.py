from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_finance_report.hooks import _create_account_analytic_plan_operating_expenses


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_account_analytic_plan_operating_expenses(env)
