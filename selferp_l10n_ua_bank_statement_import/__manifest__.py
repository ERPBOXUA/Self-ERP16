{
    'name': 'Import Bank Statement from Excel/CSV file for Ukraine',
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
    'summary': """Import Bank Statement from Excel/CSV file for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png'
    ],

    'depends': [
        'account_bank_statement_import',
        'account_bank_statement_import_csv',
        'l10n_ua',
        'web_enterprise',
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/account_bank_statement_import_mapping_data.xml',

        'views/account_bank_statement_import_mapping_views.xml',
        'views/account_journal_views.xml',
    ],
}
