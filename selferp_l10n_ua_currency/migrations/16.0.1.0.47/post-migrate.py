def migrate(cr, version):
    cr.execute('''
        UPDATE account_move
           SET is_import_vendor_bill = True
         WHERE id IN (SELECT vendor_bill_id FROM stock_picking WHERE vendor_bill_id IS NOT NULL)
    ''')
