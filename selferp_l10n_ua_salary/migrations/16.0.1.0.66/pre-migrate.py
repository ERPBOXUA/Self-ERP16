from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    structure_ua_salary_employee = env['ir.model.data'].search([
        ('name', '=', 'structure_ua_salary_employee'),
        ('module', '=', 'selferp_l10n_ua_salary'),
        ('model', '=', 'hr.payroll.structure')
    ])
    if structure_ua_salary_employee:
        structure_ua_salary_employee.noupdate = False
