def migrate(cr, version):
    cr.execute('''
        UPDATE res_country_state
           SET code = concat('_', code),
               name = concat('_', name)
         WHERE country_id IN (
               SELECT id
                 FROM res_country
                WHERE code = 'UA'
         )
    ''')
