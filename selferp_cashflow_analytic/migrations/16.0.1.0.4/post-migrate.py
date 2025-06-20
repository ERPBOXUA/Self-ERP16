from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('analytic.account_analytic_plan_action', False)
    if action:
        action.context = "{}"
