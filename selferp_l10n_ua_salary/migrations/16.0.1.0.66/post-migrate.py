from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'uk_UA'})
    update_rules(env)
