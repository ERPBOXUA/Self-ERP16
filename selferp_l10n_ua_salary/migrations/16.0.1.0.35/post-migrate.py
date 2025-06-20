import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    struct_data = {
        (data['code'], data['category_id']): data
        for (cmd, res_id, data) in env['hr.payroll.structure']._get_default_rule_ids()
        if data and data.get('code') and data.get('category_id')
    }

    HrSalaryRule = env['hr.salary.rule']

    structures = HrSalaryRule.search([('code', '=', 'ADV_GROSS')]).mapped('struct_id')

    for structure in structures:
        rules = {(rule.code, rule.category_id.id): rule for rule in structure.rule_ids.filtered(lambda rec: rec.active)}
        for rule_key, values in struct_data.items():
            if values:
                values['struct_id'] = structure.id
                rule = rules.get(rule_key)
                if not rule:
                    _logger.info("Creating rule %s (cat: %s)" % rule_key)
                    HrSalaryRule.create(values)
                else:
                    rule.write(values)
