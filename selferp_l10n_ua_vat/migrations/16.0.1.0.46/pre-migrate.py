from odoo import api, SUPERUSER_ID
from odoo.tools import table_exists


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if table_exists(cr, 'account_benefit_code'):
        env.cr.execute('''
            DELETE FROM account_benefit_code
        ''')

    env.cr.execute('''
        DELETE FROM ir_model_data
         WHERE model = 'account.benefit_code'
    ''')
