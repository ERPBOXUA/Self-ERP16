from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _set_stock_inventory_sequences(env)


def _set_stock_inventory_sequences(env):
    companies = env['res.company'].with_context(active_test=False).search([])
    companies._setup_stock_inventory_sequences()
