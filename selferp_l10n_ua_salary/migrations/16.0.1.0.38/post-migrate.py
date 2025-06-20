import logging

from odoo import api, SUPERUSER_ID
from odoo.tools import mute_logger


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    structures = env['hr.salary.rule'].search([('code', '=', 'ADV_GROSS')]).mapped('struct_id')
    supp_min_wage = structures.mapped('rule_ids').filtered(lambda rec: rec.code == 'SUPP_MIN_WAGE')
    if supp_min_wage:
        supp_min_wage.write({'sequence': 80})

    leave115_old = env['hr.work.entry.type'].search([('code', '=', '_LEAVE115')])
    if leave115_old:
        leave115 = env.ref('selferp_l10n_ua_salary.hr_work_entry_type_maternity_leave', False)
        if leave115:
            try:
                with mute_logger('odoo.sql_db'):
                    leave115.unlink()
            except Exception as ex:
                _logger.info('Cannot delete record:' + ex.faultString)
                leave115.code = 'LEAVE115_OLD'
        leave115_old.code = 'LEAVE115'
        leave115_data = env['ir.model.data'].search([
            ('model', '=', 'hr.work.entry.type'),
            ('module', '=', 'selferp_l10n_ua_salary'),
            ('name', '=', 'hr_work_entry_type_maternity_leave'),
        ])
        if leave115_data:
            leave115_data.res_id = leave115_old.id
        else:
            env['ir.model.data'].create({
                'name': 'hr_work_entry_type_maternity_leave',
                'module': 'selferp_l10n_ua_salary',
                'model': 'hr.work.entry.type',
                'res_id': leave115_old.id,
                'noupdate': False,
            })
