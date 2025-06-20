from odoo import api, SUPERUSER_ID
from odoo.tools import table_exists


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if table_exists(cr, 'account_move_vat_adjustment_line'):
        env.flush_all()
        env.cr.execute('''
             INSERT INTO account_move_vat_line (
                    move_id,
                    sequence,
                    adjustment_num_line_vat_invoice,
                    product_id,
                    product_uom_id,
                    vat_tax_id,
                    adjustment_reason_type,
                    adjustment_group,
                    name,
                    price_unit,
                    total,
                    vat_amount,
                    quantity
             )
             SELECT move_id,
                    sequence,
                    num_line_vat_invoice,
                    product_id,
                    product_uom_id,
                    vat_tax_id,
                    reason_type,
                    adjustment_group,
                    name,
                    price_unit,
                    total,
                    vat_amount,
                    quantity
               FROM account_move_vat_adjustment_line
        ''')

        env.cr.execute('''
            DROP TABLE account_move_vat_adjustment_line
        ''')
