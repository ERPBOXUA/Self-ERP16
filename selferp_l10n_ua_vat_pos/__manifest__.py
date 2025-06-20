{
    'name': 'Retail trade VAT accounting for Ukraine',
    'category': 'Accounting/Accounting',
    'version': '16.0.1.1.1',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': -999999,

    'author': 'Self-ERP',
    'website': 'https://www.self-erp.com',
    'support': 'apps@self-erp.com',
    'summary': """Retail trade VAT accounting for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'point_of_sale',
        'web_enterprise',

        'selferp_l10n_ua_vat',
    ],

    'data': [
        'views/pos_session_views.xml',
        'views/res_config_settings.xml',
    ],
}
