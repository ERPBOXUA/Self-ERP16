{
    'name': 'Sale print forms for Ukraine',
    'category': 'Accounting/Localizations',
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
    'summary': """Sale print forms for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'sale',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'report/account_move_reports.xml',
        'report/account_move_templates_act.xml',
        'report/account_move_templates_invoice.xml',
        'report/sale_order_reports.xml',
        'report/sale_order_templates.xml',

        'views/account_move_views.xml',
    ],
}
