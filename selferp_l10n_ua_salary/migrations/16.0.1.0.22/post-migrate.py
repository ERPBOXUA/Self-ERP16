from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'en_US'})

    struct_data = {
        data['code']: data for (cmd, res_id, data)
        in env['hr.payroll.structure']._get_default_rule_ids()
        if data and data.get('code')
    }

    vacations_data = struct_data.get('VACATIONS')
    if vacations_data:
        HrSalaryRule = env['hr.salary.rule']
        structures = HrSalaryRule.search([('code', '=', 'ADV_GROSS')]).mapped('struct_id')
        for structure in structures:
            rules = {rule.code: rule for rule in structure.rule_ids}
            if not rules.get('VACATIONS'):
                values = dict(struct_id=structure.id, **vacations_data)
                HrSalaryRule.create(values)

    benefits = env['hr.employee.tax_social_benefit'].search([('tax_social_benefit_code_id', '=', False)])
    if benefits:
        benefits.write({
            'tax_social_benefit_code_id': env.ref('selferp_l10n_ua_salary.hr_employee_tax_social_benefit_code_1').id,
        })
