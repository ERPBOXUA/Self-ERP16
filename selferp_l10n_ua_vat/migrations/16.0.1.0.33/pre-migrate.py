from odoo.tools import column_exists, rename_column


def migrate(cr, version):
    if column_exists(cr, 'account_move', 'vat_cause_type_adjustment'):
        rename_column(cr, 'account_move', 'vat_cause_type_adjustment', 'vat_cause_type_adjustment_bck')

