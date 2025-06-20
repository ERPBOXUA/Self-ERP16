{
    'name': 'Finance Reports for Ukraine',
    'category': 'Accounting/Accounting',
    'version': '16.0.1.1.2',
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
    'summary': """Finance Reports for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'account_reports',
        'analytic',
        'stock_account',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'data/account_analytic_account_template_data.xml',
        'data/account_report_balance_sheet_1_data.xml',
        'data/account_report_balance_sheet_1m_data.xml',
        'data/account_report_financial_results_2_data.xml',
        'data/account_report_financial_results_2m_data.xml',
        'data/account_report_inventory_report_data.xml',
        'data/account_report_menuitems.xml',

        'views/account_report_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'selferp_l10n_ua_finance_report/static/src/js/account_reports.js',
            'selferp_l10n_ua_finance_report/static/src/scss/account_report_inventory_report.scss',
        ],
    },

    'post_init_hook': 'post_init_hook',
}
