import logging


_logger = logging.getLogger(__name__)


def get_rbo_structures(env):
    return env['hr.salary.rule'].search([('code', '=', 'ADV_GROSS')]).mapped('struct_id')


def get_rbo_structures_data(env, income_feature_code):
    HrPayrollStructure = env['hr.payroll.structure']
    if income_feature_code:
        HrPayrollStructure = HrPayrollStructure.with_context(force_income_feature_code=income_feature_code)
    return {
        (data['code'], data['category_id']): data
        for (cmd, res_id, data) in HrPayrollStructure._get_default_rule_ids()
        if data and data.get('code') and data.get('category_id')
    }


def update_rules(env):
    HrSalaryRule = env['hr.salary.rule']

    structures = get_rbo_structures(env)
    struct_type_clc = env.ref('selferp_l10n_ua_salary.hr_payroll_structure_type_civil_law_contract', False)

    for structure in structures:
        rules = {(rule.code, rule.category_id.id): rule for rule in structure.rule_ids}
        struct_data = get_rbo_structures_data(env, structure.type_id == struct_type_clc and '102' or '101')
        for rule_key, rule_values in struct_data.items():
            if rule_values:
                values = dict(rule_values)
                values['struct_id'] = structure.id
                rule = rules.get(rule_key)
                if not rule:
                    _logger.info("Creating rule %s (cat: %s)" % rule_key)
                    HrSalaryRule.create(values)
                else:
                    if 'account_debit_code' not in values:
                        values['account_debit_code'] = None
                    if 'account_credit_code' not in values:
                        values['account_credit_code'] = None
                    rule.write(values)
