# -*- coding: utf-8 -*-
{
    'name': 'Export VAT for Ukraine',
    'category': 'Accounting/Accounting',
    'version': '16.0.1.1.1',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': True,
    'sequence': -999999,

    'author': 'Self-ERP',
    'website': 'https://www.self-erp.com',
    'support': 'apps@self-erp.com',
    'summary': """Export VAT for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'web_enterprise',

        'selferp_l10n_ua_currency',
        'selferp_l10n_ua_vat',
    ],

    'data': [
        'views/account_move_views.xml',
    ],
}
