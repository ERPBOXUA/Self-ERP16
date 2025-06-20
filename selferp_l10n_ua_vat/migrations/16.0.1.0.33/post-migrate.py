from odoo.tools import column_exists


def migrate(cr, version):
    if column_exists(cr, 'account_move', 'vat_cause_type_adjustment_bck'):
        cr.execute('''
            UPDATE account_move_vat_line
               SET adjustment_cause_type = move.vat_cause_type_adjustment_bck
              FROM account_move as move
             WHERE move_id = move.id
               AND move.move_type = 'vat_adjustment_invoice'
        ''')
        cr.execute('''
            ALTER TABLE account_move
             DROP COLUMN vat_cause_type_adjustment_bck
        ''')
