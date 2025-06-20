from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    leave115 = env['hr.work.entry.type'].search([('code', '=', 'LEAVE115')])
    if leave115:
        leave115.write({'code': '_LEAVE115'})
