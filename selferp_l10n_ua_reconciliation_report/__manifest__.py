{
    'name': 'Reconciliation report print form for Ukraine',
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
    'summary': """Reconciliation report print form for Ukraine""",

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
        'data/partner_ledger.xml',

        'report/report_reconciliation_templates.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'selferp_l10n_ua_reconciliation_report/static/src/js/account_reports.js',
        ],
    },
}
