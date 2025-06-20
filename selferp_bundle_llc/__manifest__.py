{
    'name': 'Accounting for Ukraine',
    'category': 'Accounting/Accounting',
    'version': '16.0.1.1.1',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': -999999,

    'author': 'Self-ERP',
    'website': 'https://www.self-erp.com',
    'support': 'apps@self-erp.com',
    'summary': """
This module contains a set of modules from Self-ERP that add functionality 
for maintaining regulated accounting in accordance with the requirements 
of Ukrainian legislation. This module will be of interest to legal entities 
that are Not VAT payers.""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_accountant',
        'hr',
        'purchase',
        'sale_management',
        'stock',
        'web_enterprise',

        'selferp_accountable_person',
        'selferp_contract_settlement',
        'selferp_l10n_ua_consignment_note',
        'selferp_l10n_ua_currency',
        'selferp_l10n_ua_ext',
        'selferp_l10n_ua_finance_report',
        'selferp_l10n_ua_fixed_asset',
        'selferp_l10n_ua_reconciliation_report',
        'selferp_l10n_ua_salary',
        'selferp_l10n_ua_sale_print_form',
    ],
}
