{
    'name': 'Cash flow analytic items',
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
    'summary': """Cash flow analytic items""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_accountant',
        'web_enterprise',

        'selferp_l10n_ua_ext',
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/account_analytic_account_template_data.xml',
        'data/account_report_cash_flow_analytic_data.xml',

        'views/account_analytic_line_views.xml',
        'views/account_analytic_plan_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/account_move_line_views.xml',
        'views/account_report_menus.xml',
        'views/bank_rec_widget_views.xml',

        'wizard/move_line_analytic_link_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'selferp_cashflow_analytic/static/src/js/move_line_analytic_link_widget.js',
            'selferp_cashflow_analytic/static/src/xml/move_line_analytic_link_widget_templates.xml',
        ],
    },

    'post_init_hook': 'post_init_hook',
}
