
def migrate(cr, version):
    cr.execute('''
        UPDATE ir_model_data
           SET module = 'selferp_l10n_ua_ext'
        WHERE model = 'account.tax.inspection' 
          AND module = 'selferp_l10n_ua_vat' 
    ''')
