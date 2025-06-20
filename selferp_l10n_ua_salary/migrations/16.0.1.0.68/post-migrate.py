from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'uk_UA'})
    structure_data_new = env['ir.model.data'].search([
        ('name', '=', 'hr_payroll_structure_ua_salary_employee'),
        ('module', '=', 'selferp_l10n_ua_salary'),
        ('model', '=', 'hr.payroll.structure')
    ])
    structure_data_old = env['ir.model.data'].search([
        ('name', '=', 'structure_ua_salary_employee'),
        ('module', '=', 'selferp_l10n_ua_salary'),
        ('model', '=', 'hr.payroll.structure')
    ])
    if structure_data_old and structure_data_old.res_id:
        if structure_data_new:
            structure_new = structure_data_new.res_id and env['hr.payroll.structure'].browse(structure_data_new.res_id) or None
            if structure_new:
                structure_new.unlink()
            structure_data_new.unlink()
        structure_data_old.name = 'hr_payroll_structure_ua_salary_employee'

    update_rules(env)
