from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # replace existing XML-IDs
    root_plan = env.ref('selferp_cashflow_analytic.analytic_plan_cash_flow', raise_if_not_found=False)
    if root_plan:
        cr.execute('''
            UPDATE ir_model_data
               SET name = '%s_account_'||name
             WHERE module = 'selferp_cashflow_analytic'
               AND name LIKE 'analytic_plan_%%'
        ''' % root_plan.company_id.id)

        cr.execute('''
            UPDATE ir_model_data
               SET name = '%s_account_'||name
             WHERE module = 'selferp_cashflow_analytic'
               AND name LIKE 'analytic_account_%%'
        ''' % root_plan.company_id.id)
