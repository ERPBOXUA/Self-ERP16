{
    'name': 'Consignment note print form for Ukraine',
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
    'summary': """Consignment note print form for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'sale_stock',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'report/stock_picking_reports.xml',
        'report/stock_picking_templates.xml',

        'views/stock_picking_views.xml',
    ],
}
