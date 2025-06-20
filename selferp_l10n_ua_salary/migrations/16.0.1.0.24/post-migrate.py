import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'uk_UA'})

    paid_leaves = env['hr.leave'].search([]).filtered(
        lambda rec:
               rec.holiday_status_id
               and rec.holiday_status_id.work_entry_type_id
               and rec.holiday_status_id.work_entry_type_id.code == 'LEAVE120'
               and rec.payslip_state != 'done'
    )
    if paid_leaves:
        paid_leaves.write({
            'payslip_state': 'done',
        })
