from odoo import api, SUPERUSER_ID


from odoo.addons.selferp_l10n_ua_finance_report.hooks import create_analytic_operating_expenses


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    plan_template = env.ref(
        xml_id='selferp_l10n_ua_finance_report.account_analytic_plan_template_operating_expenses',
        raise_if_not_found=False,
    )
    if plan_template:
        unavailable_plans = env['account.analytic.plan'].search(
            [
                ('plan_template_id', '=', plan_template.id),
                ('default_applicability', '=', 'unavailable'),
                ('description', '=like', 'Unavailable due to creation error.%'),
            ]
        )
        for plan in unavailable_plans:
            plan.write(
                {
                    'active': False,
                    'default_applicability': 'optional',
                    'description': plan.description.replace('Unavailable due to creation error. ', ''),
                }
            )

    create_analytic_operating_expenses(env)
