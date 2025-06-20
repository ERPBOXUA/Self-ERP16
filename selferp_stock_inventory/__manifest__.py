{
    'name': 'Stock Inventory for Ukraine',
    'category': 'Inventory',
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
    'summary': """Stock Inventory for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'hr',
        'stock_account',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/stock_inventory_security.xml',

        'data/stock_sequence_data.xml',

        'report/stock_inventory_reports.xml',
        'report/stock_inventory_templates.xml',

        'views/stock_inventory_views.xml',

        'wizard/stock_request_count.xml',
    ],

    'post_init_hook': 'post_init_hook',
}
