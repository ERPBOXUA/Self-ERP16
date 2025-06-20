from odoo import api, SUPERUSER_ID
from odoo.tools import config


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    create_analytic_operating_expenses(env)


def create_analytic_operating_expenses(env, company=None):
    companies = company or env['res.company'].with_context(active_test=False).search([])

    env['account.analytic.plan.template'].create_analytic_plan(
        companies,
        'selferp_l10n_ua_finance_report.account_analytic_plan_template_operating_expenses',
    )


def _delete_report(env, xml_id):
    report = env.ref(xml_id, raise_if_not_found=False)
    if report:
        report.unlink()
