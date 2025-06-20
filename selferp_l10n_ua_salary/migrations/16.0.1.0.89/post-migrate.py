import logging

from odoo import api, SUPERUSER_ID
from odoo.tools import mute_logger

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import update_rules


_logger = logging.getLogger(__name__)


def _inactivate_work_entry_type(env, existing_rec, new_rec, xml_id):
    if existing_rec and new_rec:
        try:
            with env.cr.savepoint(), mute_logger('odoo.sql_db'):
                existing_rec.unlink()
        except Exception as ex:
            _logger.info('Cannot delete record:' + str(ex))
            existing_rec.active = False

        module, rec_name = xml_id.split('.')
        data = env['ir.model.data'].search([
            ('model', '=', 'hr.work.entry.type'),
            ('module', '=', module),
            ('name', '=', rec_name),
        ])
        if data:
            data.res_id = new_rec.id
        else:
            env['ir.model.data'].create({
                'name': rec_name,
                'module': module,
                'model': 'hr.work.entry.type',
                'res_id': new_rec.id,
                'noupdate': False,
            })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _inactivate_work_entry_type(
        env,
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', '_ТВ')]),
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', 'ТВ')]),
        'selferp_l10n_ua_salary.hr_work_entry_type_creative_leave',
    )
    _inactivate_work_entry_type(
        env,
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', '_ВД')]),
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', 'ВД')]),
        'selferp_l10n_ua_salary.work_entry_type_business_trip',
    )
    _inactivate_work_entry_type(
        env,
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', '_Д')]),
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', 'Д')]),
        'selferp_l10n_ua_salary.hr_work_entry_annual_additional_leave',
    )
    _inactivate_work_entry_type(
        env,
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', '_ІН')]),
        env['hr.work.entry.type'].search([('timesheet_ccode', '=', 'ІН')]),
        'selferp_l10n_ua_salary.work_entry_type_leave_legal',
    )

    update_rules(env)
