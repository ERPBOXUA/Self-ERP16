from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.cr.execute('''
        ALTER TABLE IF EXISTS hr_job_class DROP CONSTRAINT IF EXISTS hr_job_class_code_uniq;
    ''')
