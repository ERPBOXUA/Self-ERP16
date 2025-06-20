import logging
import psycopg2

from odoo import api, SUPERUSER_ID
from odoo.tools import mute_logger


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'uk_UA'})

    struct_data = {
        (data['code'], data['category_id']): data for (cmd, res_id, data)
        in env['hr.payroll.structure']._get_default_rule_ids()
        if data and data.get('code') and data.get('category_id')
    }

    HrSalaryRule = env['hr.salary.rule']

    def _find_rule(rules, code, category_id=None, pyton_code=None, condition_python=None):
        result = HrSalaryRule
        for rec in rules:
            if (
                rec.code == code
                and (not category_id or rec.category_id.id == category_id)
                and (not condition_python or (rec.condition_select == 'python' and rec.condition_python == condition_python))
                and (not pyton_code or (rec.amount_select == 'code' and rec.amount_python_compute == pyton_code))
            ):
                result |= rec
        if result:
            result = result.sorted(key=lambda rec: (rec.sequence, rec.id))
        return result

    # The goal is to update the rules and make them uniquely identifiable by (code, categ_id) for future updates
    structures = HrSalaryRule.search([('code', '=', 'ADV_GROSS')]).mapped('struct_id')
    for structure in structures:
        _logger.info("Processing structure %s (%s)" % (structure.name, structure.id))

        struct_rules = {}
        all_rules = structure.rule_ids.filtered(lambda rec: rec.active)

        # Known code remapping
        rule = _find_rule(all_rules, 'VACATIONS')
        if rule:
            all_rules -= rule[0]
            struct_rules[('VACATIONS_GROSS', env.ref('hr_payroll.GROSS').id)] = rule[0]
        rule = _find_rule(all_rules, 'ADV', env.ref('hr_payroll.DED').id)
        if rule:
            all_rules -= rule[0]
            struct_rules[('ADV_PAID', rule[0].category_id.id)] = rule[0]
        rule = _find_rule(all_rules, 'ADV_ESV')
        if rule:
            all_rules -= rule[0]
            struct_rules[('ADV_ESV_PAID', env.ref('selferp_l10n_ua_salary.ESV').id)] = rule[0]
        rule = _find_rule(all_rules, 'ADV_PDFO', env.ref('selferp_l10n_ua_salary.PDFO').id)
        if rule:
            all_rules -= rule
            struct_rules[('ADV_PDFO_PAID', rule[0].category_id.id)] = rule
        rule = _find_rule(all_rules, 'ADV_MT', env.ref('selferp_l10n_ua_salary.MT').id)
        if rule:
            all_rules -= rule
            struct_rules[('ADV_MT_PAID', rule[0].category_id.id)] = rule
        rule = _find_rule(all_rules, 'ADV_ESV', env.ref('selferp_l10n_ua_salary.ESV').id)
        if rule:
            all_rules -= rule[0]
            struct_rules[('ADV_ESV', rule[0].category_id.id)] = rule[0]
        rule = _find_rule(all_rules, 'ADV_PDFO', env.ref('hr_payroll.DED').id)
        if rule:
            all_rules -= rule[0]
            struct_rules[('ADV_PDFO', rule[0].category_id.id)] = rule[0]
        rule = _find_rule(all_rules, 'ADV_MT', env.ref('hr_payroll.DED').id)
        if rule:
            all_rules -= rule[0]
            struct_rules[('ADV_MT', rule[0].category_id.id)] = rule[0]

        struct_rules.update({(rule.code, rule.category_id.id): rule for rule in all_rules})

        for rule_key, values in struct_data.items():
            if values:
                values['struct_id'] = structure.id
                rule = struct_rules.get(rule_key)
                if rule:
                    struct_rules.pop(rule_key)
                    _logger.info("Updating rule %s (cat: %s)" % rule_key)
                    rule.write(values)
                else:
                    _logger.info("Creating rule %s (cat: %s)" % rule_key)
                    HrSalaryRule.create(values)

        if struct_rules:
            deactivate = HrSalaryRule
            for rule in struct_rules.values():
                _logger.info("Trying to remove rule %s (cat: %s)" % (rule.code, rule.category_id.id))
                try:
                    with cr.savepoint(), mute_logger('odoo.sql_db'):
                        rule.unlink()
                except psycopg2.Error as ex:
                    _logger.info(ex)
                    _logger.info("DB check constrains failed, the rule will be deactivated")
                    deactivate |= rule
            if deactivate:
                deactivate.write({'active': False})
