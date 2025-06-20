from odoo import api, SUPERUSER_ID
from odoo.tools import config

from .models.res_users import _install_analytics


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    group_account_user = env.ref('account.group_account_user', raise_if_not_found=False)
    if group_account_user:
        accountants = env['res.users'].search([('groups_id', 'in', group_account_user.ids)])
        if accountants:
            _install_analytics(accountants, immediate_dependencies=False)

    # populate analytic plan to all companies
    create_analytic_plan_cash_flow(env)


def create_analytic_plan_cash_flow(env, company=None):
    if config['test_enable']:
        # skip plan population on tests
        return

    companies = company or env['res.company'].with_context(active_test=False).search([])

    env['account.analytic.plan.template'].create_analytic_plan(
        companies,
        'selferp_cashflow_analytic.account_analytic_plan_template_cash_flow',
    )
