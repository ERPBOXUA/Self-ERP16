from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['hr.order.type.group'].create_sequences_for_all_type_groups(env['hr.order.type.group'].sudo().search([]))
