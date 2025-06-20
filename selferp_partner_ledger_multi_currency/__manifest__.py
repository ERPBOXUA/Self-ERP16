{
    'name': 'Multi Currency Partner Ledger',
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
    'summary': """Multi Currency Partner Ledger""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'web_enterprise',

        'selferp_contract_settlement',
    ],

    'data': [
        'data/account_report_partner_ledger_multi_currency_data.xml',

        'views/account_menuitem.xml',
    ],
}
