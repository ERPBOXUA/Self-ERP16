from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Just to meet 'required' restriction on existing data
    env.cr.execute('''
        UPDATE hr_schedule
           SET basis = 'Add basis here!'
         WHERE basis IS NULL 
    ''')
