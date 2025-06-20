{
    'name': 'Extension of Ukrainian localization',
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
    'summary': """Extension of Ukrainian localization""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_accountant',
        'account_reports',
        'l10n_ua',
        'purchase',
        'sale',
        'stock',
        'web_enterprise',
    ],

    'external_dependencies': {
        'python': [
            'num2words',
        ],
    },

    'data': [
        'security/ir.model.access.csv',

        'data/account_tax_inspection_data.xml',
        'data/partner_ledger.xml',
        'data/product_dkpp_code_data.xml',
        'data/product_uktzed_code_data.xml',
        'data/res_country_state_data.xml',

        'report/account_editable_report_templates.xml',
        'report/export_xml_templates.xml',
        'report/report_layout_light_custom_templates.xml',
        'report/report_layout_light_custom.xml',

        'views/account_editable_report_templates.xml',
        'views/report_templates.xml',

        'views/account_analytic_account_views.xml',
        'views/account_analytic_plan_views.xml',
        'views/account_editable_report_views.xml',
        'views/account_report_views.xml',
        'views/account_tax_inspection_views.xml',
        'views/product_dkpp_code_views.xml',
        'views/product_template_views.xml',
        'views/product_uktzed_code_views.xml',
        'views/res_company_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',

        'views/menuitem.xml',
    ],

    'assets': {
        'web.report_assets_common': [
            'selferp_l10n_ua_ext/static/src/scss/report_layout_light_custom.scss',
            'selferp_l10n_ua_ext/static/src/scss/report_common_fonts.scss',
            'selferp_l10n_ua_ext/static/src/scss/account_editable_report_commons.scss',
        ],
        'web.assets_backend': [
            'selferp_l10n_ua_ext/static/src/js/account_reports.js',
            'selferp_l10n_ua_ext/static/src/js/*.esm.js',
            'selferp_l10n_ua_ext/static/src/views/**/*',

            'selferp_l10n_ua_ext/static/src/scss/search/**/*.scss',

            'selferp_l10n_ua_ext/static/src/scss/account_editable_report_commons.scss',
        ],
        'web.assets_frontend': [
            'selferp_l10n_ua_ext/static/src/scss/account_editable_report_page_container.scss',
            'selferp_l10n_ua_ext/static/src/scss/account_editable_report_commons.scss',

            'selferp_l10n_ua_ext/static/src/js/account_editable_report.js',
        ],
    },

    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
