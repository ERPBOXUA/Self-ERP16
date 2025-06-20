from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_l10n_ua_salary.hooks import _set_pdfo_sequences


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_pdfo_sequences(env)
