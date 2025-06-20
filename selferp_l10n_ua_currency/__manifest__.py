{
    'name': 'FEA for Ukraine',
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
    'summary': """FEA for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'account_accountant',
        'currency_rate_live',
        'purchase',
        'purchase_stock',
        'stock',
        'stock_landed_costs',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/product_product.xml',

        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
    ],

    'post_init_hook': 'post_init_hook',
}
