from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_ext.hooks import _update_asset_account_type


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _update_asset_account_type(env)
