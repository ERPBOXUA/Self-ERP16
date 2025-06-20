from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_cashflow_analytic.hooks import create_analytic_plan_cash_flow


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # populate analytic plan to all companies
    create_analytic_plan_cash_flow(env)
