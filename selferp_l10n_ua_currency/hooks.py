from odoo import api, SUPERUSER_ID
from odoo.addons.selferp_l10n_ua_currency.models.account_chart_template import try_load_default_accounts


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([]):
        try_load_default_accounts(env, company)
