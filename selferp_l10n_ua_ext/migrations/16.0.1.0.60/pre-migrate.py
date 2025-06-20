from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute('''
        UPDATE ir_model_data
           SET module = 'selferp_l10n_ua_ext'
         WHERE model = 'product.uktzed_code'
           AND module = 'selferp_l10n_ua_vat'
    ''')
    cr.execute('''
        UPDATE ir_model_data
           SET module = 'selferp_l10n_ua_ext'
         WHERE model = 'product.dkpp_code'
           AND module = 'selferp_l10n_ua_vat'
    ''')
