from odoo import api, SUPERUSER_ID


NEW_COMPUTE_ESV = '''rate = 0.0841 if employee.has_actual_disability_group(payslip.date_from) else 0.22
result = round(payslip.dict.fix_esv_base(GROSS) * rate)'''

NEW_COMPUTE_ESV_ADV = '''rate = 0.0841 if employee.has_actual_disability_group(payslip.date_from) else 0.22
result = round(ADV_GROSS * rate)'''


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'en_US'})

    rules = env['hr.salary.rule'].search([('code', 'in', ('ADV_ESV', 'ESV'))])
    for rule in rules:
        rule.amount_python_compute = NEW_COMPUTE_ESV_ADV if rule.code == 'ADV_ESV' else NEW_COMPUTE_ESV
