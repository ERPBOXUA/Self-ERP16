from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'en_US'})

    structures = env['hr.salary.rule'].search([('code', '=', 'ADV_NET')]).mapped('struct_id')
    if structures:
        rules_data = structures._get_default_rule_ids()
        for structure in structures:
            obsolete_rules = env['hr.salary.rule'].search([('struct_id', '=', structure.id), ('name', 'ilike', '%with disabilities')])
            if obsolete_rules:
                obsolete_rules.active = False

            basic = env['hr.salary.rule'].search([('struct_id', '=', structure.id), ('name', '=', 'Basic Salary')])
            basic.sequence = 50

            new_rules = []
            used_rule_ids = set()
            rules = {(rule.code, rule.sequence): rule for rule in structure.rule_ids}
            for rule_data in rules_data:
                key = (rule_data[2]['code'], rule_data[2]['sequence'])
                rule = rules.get(key)
                if not rule:
                    new_rules.append(rule_data)
                else:
                    rule.write(rule_data[2])
                    used_rule_ids.add(rule.id)

            if new_rules:
                structure.rule_ids = new_rules
