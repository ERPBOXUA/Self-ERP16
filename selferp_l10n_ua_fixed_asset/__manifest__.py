{
    'name': 'Fixed Assets for Ukraine',
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
    'summary': """Fixed Assets for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'account_accountant',
        'account_asset',
        'l10n_ua',
        'maintenance',
        'purchase',
        'sale',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/assert_report.xml',

        'views/account_asset_views.xml',
        'views/account_move_line_views.xml',
        'views/maintenance_views.xml',
        'views/product_views.xml',

        'wizard/asset_modify_views.xml',
    ],
}
