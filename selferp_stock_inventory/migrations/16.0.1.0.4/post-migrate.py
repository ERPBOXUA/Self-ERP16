from odoo import api, SUPERUSER_ID

from odoo.addons.selferp_stock_inventory.hooks import _set_stock_inventory_sequences


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_stock_inventory_sequences(env)
