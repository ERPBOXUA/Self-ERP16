{
    'name': 'Settlements with partners in terms of contracts',
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
    'summary': """Settlements with partners in terms of contracts""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_accountant',
        'account_reports',
        'contacts',
        'sale',
        'purchase',
        'web_enterprise',

        'selferp_l10n_ua_sale_print_form',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/account_contract_security.xml',

        'data/account_contract_data.xml',
        'data/partner_ledger.xml',

        'report/account_move_templates_act.xml',
        'report/account_move_templates_invoice.xml',
        'report/sale_order_templates.xml',

        'views/account_bank_statement_line_views.xml',
        'views/account_contract_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
        'views/bank_rec_widget_views.xml',
        'views/purchase_views.xml',
        'views/res_partner_views.xml',
        'views/sale_views.xml'
    ],

    'assets': {
        'account_reports.assets_financial_report': [
            'selferp_contract_settlement/static/src/scss/account_financial_report.scss',
        ],
        'web.assets_backend': [
            'selferp_contract_settlement/static/src/scss/account_financial_report.scss',
        ],
    },
}
