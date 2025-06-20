from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    plan = env.ref(
        xml_id='selferp_l10n_ua_finance_report.account_analytic_plan_operating_expenses',
        raise_if_not_found=False,
    )
    if plan:
        plan.account_ids.action_archive()
        plan.write({'default_applicability': 'unavailable', 'description': f'Unavailable due to creation error. {plan.description}'})
