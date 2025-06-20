import logging

from odoo import api, SUPERUSER_ID
from odoo.tools import mute_logger

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_rules(env)

    std_leaves_data = env['ir.model.data'].search([('model', '=', 'hr.leave.type')])
    std_leave_type_ids = [rec.res_id for rec in std_leaves_data]
    custom_leaves = env['hr.leave.type'].search([('id', 'not in', std_leave_type_ids)])
    for leave in custom_leaves:
        try:
            with env.cr.savepoint(), mute_logger('odoo.sql_db'):
                leave.unlink()
        except Exception as ex:
            _logger.info('Cannot delete record:' + str(ex))
            leave.active = False

