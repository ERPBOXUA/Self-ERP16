from odoo.tools import convert_file


def migrate(cr, version):
    convert_file(
        cr,
        'selferp_l10n_ua_vat',
        'data/account_tax_inspection_data.xml',
        {},
        'init',
        False,
        'data',
    )
