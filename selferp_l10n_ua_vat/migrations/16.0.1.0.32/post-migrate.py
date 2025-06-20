from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_vat.hooks import _set_vat_sequences


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_vat_sequences(env)
