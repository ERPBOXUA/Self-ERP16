from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    struct_type_cph = env['hr.payroll.structure.type'].search([('name', '=', 'ЦПХ')])
    if struct_type_cph:
        related_structures = env['hr.payroll.structure'].search([('type_id', '=', struct_type_cph.id)])
        if related_structures:
            structure_type_civil_law_contract = env.ref('selferp_l10n_ua_salary.hr_payroll_structure_type_civil_law_contract')
            related_structures.write({'type_id': structure_type_civil_law_contract.id})
        struct_type_cph.unlink()

    update_rules(env)
