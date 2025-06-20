from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    structures = env['hr.payroll.structure'].with_context(active_test=False).search([])
    for rule in structures.mapped('rule_ids').filtered(lambda rec: rec.sequence == 83 and rec.category_id.code == 'ALW'):
        rule.code = 'ACCRUAL'
        rule.sequence = 88

    update_rules(env)
