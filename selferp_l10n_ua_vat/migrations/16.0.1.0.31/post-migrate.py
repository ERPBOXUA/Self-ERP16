from odoo import api, SUPERUSER_ID
from odoo.tools import table_exists


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.flush_all()
    env.cr.execute('''
         UPDATE account_move_vat_line 
            SET total_manual = total
    ''')
