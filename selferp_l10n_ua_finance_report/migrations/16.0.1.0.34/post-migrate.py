from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    plan_template = env.ref(
        xml_id='selferp_l10n_ua_finance_report.account_analytic_plan_template_operating_expenses',
        raise_if_not_found=False,
    )
    if plan_template:
        plans_ids = env['ir.model.data'].search([
            ('module', '=', 'selferp_l10n_ua_finance_report'),
            ('model', '=', 'account.analytic.plan'),
        ]).mapped('res_id')

        env['account.analytic.plan'].search([
            ('id', 'in', plans_ids),
            ('parent_id', '=', False),
        ]).write({'plan_template_id': plan_template.id})

        cr.execute('''
            DELETE FROM ir_model_data 
             WHERE module = 'selferp_l10n_ua_finance_report' 
               AND model IN ('account.analytic.account', 'account.analytic.plan');
        ''')
