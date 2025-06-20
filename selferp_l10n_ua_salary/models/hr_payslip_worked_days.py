from odoo import models, fields, api
from odoo.tools import float_round, float_is_zero


# TODO: Check actual type codes of paid working days (work entry type for 'LEAVE_UA17' is not defined yet)
AMOUNT_AWARE_TYPE_CODES = (
    'WORK100',
    'WORK_UA03',
    'WORK_UA04',
    'WORK_UA06',
    'LEAVE120',
    'LEAVE110',
    'LEAVE_UA16',
    'LEAVE_UA17',
    'LEAVE_UA07',
)


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    contract_id = fields.Many2one(
        comodel_name='hr.contract',
        string="Contract",
        related=None,
        readonly=True,
    )

    @api.depends(
        'is_paid',
        'number_of_hours',
        'payslip_id',
        'payslip_id.contract_id',
        'payslip_id.contract_id.wage',
        'contract_id.wage',
        'payslip_id.sum_worked_hours',
        'payslip_id.payment_type',
        'payslip_id.salary_advance_calculation',
        'payslip_id.salary_advance_percents',
    )
    def _compute_amount(self):
        for worked_days in self:
            payslip = worked_days.payslip_id
            if payslip.edited or payslip.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT':
                worked_days.amount = 0
                continue
            if worked_days.code not in AMOUNT_AWARE_TYPE_CODES:
                worked_days.amount = 0
                continue
            if payslip.payment_type == 'advance_salary' and worked_days.code == 'WORK100':
                worked_days.amount = payslip.adv_salary()
            elif worked_days.code == 'LEAVE120':
                if payslip.payment_type != 'vacations':
                    related = payslip.find_related_payslips('vacations')
                    if related:
                        worked_days.amount = sum(related.mapped('line_ids').filtered(lambda rec: rec.code == 'VACATIONS_GROSS').mapped('amount'))
                        continue
                    else:
                        payslip = payslip.with_context(force_type='vacations')
                worked_days.amount = worked_days.number_of_days * (payslip.get_average_daily_wage_for_vacations() or 0.0)
            elif worked_days.code in ('LEAVE110', 'LEAVE_UA16', 'LEAVE_UA17'):
                if payslip.payment_type != 'sick_leaves':
                    if worked_days.code == 'LEAVE110':
                        related = payslip.find_related_payslips('sick_leaves')
                        related = related and related.filtered(lambda rec: not rec.is_maternity_leave())
                        if related:
                            worked_days.amount = sum(related.mapped('line_ids').filtered(lambda rec: rec.code in ('SICK_LEAVES_EMP_GROSS', 'SICK_LEAVES_CIF_GROSS')).mapped('amount'))
                            continue
                    if worked_days.code in ('LEAVE_UA16', 'LEAVE_UA17'):
                        related = payslip.find_related_payslips('sick_leaves')
                        related = related and related.filtered(lambda rec: rec.is_maternity_leave())
                        if related:
                            worked_days.amount = sum(related.mapped('line_ids').filtered(lambda rec: rec.code == 'MATERNITY_LEAVES_GROSS').mapped('amount'))
                            continue
                    payslip = payslip.with_context(force_type='sick_leaves')
                worked_days.amount = worked_days.number_of_days * (payslip.get_average_daily_wage_for_sick_leaves() or 0.0)
            elif worked_days.code == 'LEAVE_UA07':
                worked_days.amount = payslip.get_business_trip_salary()
            elif worked_days.code == 'WORK_UA03' or worked_days.code == 'WORK_UA04':
                worked_days.amount = payslip._get_overtime_salary(worked_days.code)
            elif worked_days.code == 'WORK_UA06':
                worked_days.amount = payslip.get_work_on_day_off_salary()
            else:
                if worked_days.payslip_id.wage_type == 'hourly':
                    worked_days.amount = worked_days.payslip_id.contract_id.hourly_wage * worked_days.number_of_hours if worked_days.is_paid else 0
                else:
                    scheduled_hours = (payslip._get_scheduled_time() or {}).get('hours') or 0
                    if not float_is_zero(scheduled_hours, precision_digits=2):
                        worked_days.amount = float_round(worked_days.contract_id.wage * worked_days.number_of_hours / scheduled_hours, precision_digits=2)
