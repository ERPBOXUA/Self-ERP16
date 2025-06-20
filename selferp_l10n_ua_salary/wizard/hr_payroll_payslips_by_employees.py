from odoo import models, fields


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_employees(self):
        employees = super()._get_employees()
        payslip_run_id = self.env.context.get('payslip_run_id') or self.env.context.get('active_id')
        if payslip_run_id:
            payslip_run = self.env['hr.payslip.run'].browse(payslip_run_id).exists()
            if payslip_run and payslip_run.payment_type == 'vacations':
                work_entries = self.env['hr.work.entry'].search([
                    ('work_entry_type_id.code', '=', 'LEAVE120'),
                    ('date_start', '>=', payslip_run.date_start),
                    ('date_stop', '<=', payslip_run.date_end),
                    ('state', 'in', ('draft', 'validated')),
                    ('employee_id', 'in', employees.ids),
                ])
                employees = work_entries.mapped('employee_id')
        return employees

    def _filter_contracts(self, contracts):
        if contracts:
            contracts_filtered = self.env['hr.contract']
            employee_ids = set()
            # Leave only first of contracts for period
            for contract in contracts.sorted(key=lambda rec: rec.date_start):
                if contract.employee_id.id not in employee_ids:
                    employee_ids.add(contract.employee_id.id)
                    contracts_filtered |= contract
            return contracts_filtered
        return contracts

    def compute_sheet(self):
        self.ensure_one()
        if self.env.context.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(int(self.env.context['active_id'])).exists()
            if payslip_run:
                context = dict(
                    default_payment_type=payslip_run.payment_type,
                    **self.env.context,
                )
                if payslip_run.payment_type == 'advance_salary':
                    context['default_salary_advance_calculation'] = payslip_run.salary_advance_calculation
                    if payslip_run.salary_advance_calculation == 'percentage':
                        context['default_salary_advance_percents'] = payslip_run.salary_advance_percents
                self = self.with_context(context)
        return super(HrPayslipEmployees, self).compute_sheet()
