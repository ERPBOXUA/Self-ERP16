from odoo import api, SUPERUSER_ID
from odoo.api import Environment


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    env['hr.employee']._install_employee_firstname_lastname_patronymic()
    _set_pdfo_sequences(env)

    env['hr.order.type.group'].create_sequences_for_all_type_groups(env['hr.order.type.group'].sudo().search([]))


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    payroll_action_all = env.ref('hr_payroll.action_view_hr_payslip_month_form', False)
    if payroll_action_all:
        payroll_action_all.view_mode = 'tree,kanban,form,activity'

    for order_type_group in env['hr.order.type.group'].sudo().search([]):
        for company in env['res.company'].sudo().with_context(active_test=False).search([]):
            property_seq_id = env['ir.sequence'].search([('code', '=', 'hr.order.type.group-%s_%s' % (order_type_group.id, company.id))])
            if (property_seq_id):
                property_seq_id.unlink()


def _set_pdfo_sequences(env):
    companies = env['res.company'].search([])
    companies._setup_pdfo_sequences()

