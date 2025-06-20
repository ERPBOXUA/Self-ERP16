from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    plan_template = env.ref('selferp_cashflow_analytic.account_analytic_plan_template_cash_flow', raise_if_not_found=False)

    if plan_template:
        cr.execute(f'''
            UPDATE account_analytic_plan
               SET plan_template_id = {plan_template.id}
             WHERE parent_id IS NULL 
               AND cash_flow_article
        ''')
