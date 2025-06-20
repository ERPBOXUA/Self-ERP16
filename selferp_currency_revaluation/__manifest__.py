{
    'name': 'Currency Revaluation Extension',
    'category': 'Accounting',
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
    'summary': """Currency Revaluation Extension""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_reports',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'data/multicurrency_revaluation_report.xml',

        'wizard/multicurrency_revaluation.xml',
    ],
}
