{
    'name': 'Accountable person. Alternative to HR Expense',
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
    'summary': """Accountable person. Alternative to HR Expense""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'hr',
        'l10n_ua',
        'purchase_stock',
        'web_enterprise',
    ],

    'data': [
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'views/res_partner_views.xml',
    ],

    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
