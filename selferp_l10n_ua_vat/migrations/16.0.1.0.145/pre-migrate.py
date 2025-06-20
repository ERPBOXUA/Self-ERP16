from odoo.tools import column_exists, rename_column


def migrate(cr, version):
    if column_exists(cr, 'account_account', 'first_event_vendor'):
        rename_column(cr, 'account_account', 'first_event_vendor', 'first_event_vendor_bck')

