from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['account.vat.tax_report'].with_context(allow_data_migration=True).migrate_data(24)
