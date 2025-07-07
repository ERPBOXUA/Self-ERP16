{
    'name': 'Accounting for Ukraine',
    'category': 'Services',
    'version': '17.0.7.10.0',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,

    'author': 'Self-ERP',
    'support': 'apps@self-erp.com',
    'summary': """Accounting for Ukraine""",

    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],

    'depends': [
        'base',
    ],

    'post_init_hook': 'post_init_hook',
}
