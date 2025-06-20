from odoo.tools import column_exists


def migrate(cr, version):
    if column_exists(cr, 'account_account', 'first_event_vendor_bck'):
        cr.execute('''
            UPDATE account_account
               SET first_event = first_event_vendor_bck
             WHERE first_event_vendor_bck = TRUE
        ''')
        cr.execute('''
            ALTER TABLE account_account
             DROP COLUMN first_event_vendor_bck
        ''')
