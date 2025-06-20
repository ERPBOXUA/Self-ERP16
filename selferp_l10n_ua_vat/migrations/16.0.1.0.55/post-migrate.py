from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_vat.hooks import _change_tax_group_vat


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _change_tax_group_vat(env)
