from odoo import api, SUPERUSER_ID


ASSET_ACCOUNTS = (
    (('code', '=', '372100'), 'liability_payable'),
    (('code', 'like', '13%'), 'asset_non_current'),
    (('code', 'like', '641%'), 'liability_current'),
    (('code', 'like', '641%'), 'liability_current'),
    (('code', 'like', '642%'), 'liability_current'),
    (('code', 'like', '65%'), 'liability_current'),
    (('code', 'like', '69%'), 'liability_current'),
    (('code', 'like', '39%'), 'asset_current'),
    (('code', '=', '333000'), 'asset_current'),
    (('code', '=', '334000'), 'asset_current'),
)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _update_asset_account_type(env)


def uninstall_hook(cr, registry):
    cr.execute('''
        UPDATE account_report
           SET search_template = 'account_reports.search_template'
         WHERE search_template = 'selferp_l10n_ua_ext.partner_ledger_search_template'
    ''')


def _update_asset_account_type(env, company=None):
    if company:
        companies = company
    else:
        companies = env['res.company'].with_context(active_test=False).search([])

    AccountAccount = env['account.account']

    for c in companies:
        for cur_search in ASSET_ACCOUNTS:
            account = AccountAccount.search(
                [cur_search[0]] + [('company_id', '=', c.id), ('account_type', '!=', cur_search[1])]
            )
            if account:
                account.write({'account_type': cur_search[1]})
