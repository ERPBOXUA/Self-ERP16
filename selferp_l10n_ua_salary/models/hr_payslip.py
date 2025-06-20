import logging

from collections import defaultdict
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools import config, float_round, float_is_zero, float_compare, pytz
from odoo.tools.misc import format_date

from odoo.addons.resource.models.resource import HOURS_PER_DAY

from odoo.addons.selferp_l10n_ua_salary.models.hr_employee_tax_social_benefit_code import PRECISION_TAX_SOCIAL_BENEFIT_RATE
from odoo.addons.selferp_l10n_ua_salary.models.res_company import SALARY_ADVANCE_VARIANTS, PRECISION_SALARY_ADVANCE_PERCENTAGE


PAYSLIP_TYPES = [
    ('advance_salary', "Salary Advance"),
    ('salary', "Salary"),
    ('vacations', "Vacations"),
    ('sick_leaves', "Sick Leaves"),
]

ADW_CODES = (
    'GROSS',
    'VACATIONS_GROSS',
    'SICK_LEAVES_EMP_GROSS',
    'SICK_LEAVES_CIF_GROSS',
    'MATERNITY_LEAVES_GROSS',
)

ADW_SICK_LEAVES_CODES = (
    'GROSS',
    'VACATIONS_GROSS',
)

AVG_DAYS_PER_MONTH = 30.44

PRECISION_DIGITS_TIME = 1
PRECISION_DIGITS_RATE = 3

ACCEPT_RATE_LIMIT = 1.03


_logger = logging.getLogger(__name__)


def safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _get_work_duration(date_start, date_stop):
    dt = date_stop - date_start
    return dt.days * 24 + dt.seconds / 3600


def _time_is_zero(value):
    return float_is_zero(value, precision_digits=PRECISION_DIGITS_TIME)


def _months_between_dates(dt_from, dt_to):
    dates = [dt for dt in rrule(MONTHLY, dtstart=dt_from, until=dt_to)]
    return dates and len(dates) or None


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payment_type = fields.Selection(
        selection=PAYSLIP_TYPES,
        string="Payment Type",
        required=True,
        default='salary',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]},
    )

    salary_advance_calculation = fields.Selection(
        selection=SALARY_ADVANCE_VARIANTS,
        string="Salary Advance Calculation",
        default=lambda self: self.env.company.salary_advance_calculation,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]},
    )

    salary_advance_calculation_editable = fields.Boolean(
        string="Salary Advance Calculation Editable",
        compute='_compute_salary_advance_calculation_editable',
    )

    salary_advance_percents = fields.Float(
        string="Salary Percentage",
        digits=PRECISION_SALARY_ADVANCE_PERCENTAGE,
        default=lambda self: self.env.company.salary_advance_percents,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]},
    )

    pdfo_amount = fields.Monetary(
        string="PDFO",
        compute='_compute_lines_deductions',
        store=True,
    )

    mt_amount = fields.Monetary(
        string="MT",
        compute='_compute_lines_deductions',
        store=True,
    )

    esv_amount = fields.Monetary(
        string="ESV",
        compute='_compute_lines_deductions',
        store=True,
    )

    payslip_run_id = fields.Many2one(
        domain="[('company_id', 'in', [company_id, False]), ('payment_type', '=', payment_type)]",
    )

    average_daily_wage = fields.Monetary(
        string="Average Daily Wage",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]},
    )

    average_daily_wage_effective = fields.Monetary(
        string="Effective Average Daily Wage",
        readonly=True,
    )

    average_daily_wage_effective_explanation = fields.Char(
        string="Effective Average Daily Wage Explanation",
        readonly=True,
    )

    average_daily_wage_effective_explanation_visible = fields.Boolean(
        string="Effective Average Daily Wage Explanation Visible",
        compute='_compute_average_daily_wage_effective_explanation_visible',
    )

    average_daily_wage_effective_visible = fields.Boolean(
        string="Is Effective Average Daily Wage Visible",
        compute='_compute_average_daily_wage_effective_visible',
    )

    journal_id = fields.Many2one(
        readonly=True,
    )

    payment_ids = fields.One2many(
        comodel_name='account.bank.statement.line',
        inverse_name='payslip_id',
        string="Payments",
    )
    payment_count = fields.Monetary(
        compute='_compute_payments',
        string="Payment Count",
    )
    payment_amount = fields.Monetary(
        compute='_compute_payments',
        string="Payment Amount",
    )

    benefit_line_ids = fields.One2many(
        comodel_name='hr.payslip.benefit.line',
        inverse_name='payslip_id',
        string="Benefit Lines",
    )

    @api.constrains('payment_type', 'employee_id', 'date_from', 'date_to', 'state', 'worked_days_line_ids')
    def _check_payment_type(self):
        if not config['test_enable'] or self.env.context.get('payslip_test_force_check_overlapped'):
            active_states = ('verify', 'done', 'paid')
            for rec in self.filtered(lambda slip: slip.state in active_states and slip.payment_type in ('salary', 'advance_salary')):
                overlapped = self.env['hr.payslip'].search([
                    ('id', '!=', rec.id),
                    ('employee_id', '=', rec.employee_id.id),
                    ('payment_type', '=', rec.payment_type),
                    ('state', 'in', active_states),
                    ('credit_note', '=', rec.credit_note),
                    '|',
                        '&', ('date_from', '>=', rec.date_from), ('date_from', '<=', rec.date_to),
                        '&', ('date_to', '>=', rec.date_from), ('date_to', '<=', rec.date_to),
                ])
                if overlapped:
                    overlapped_names = '\n'.join(['%s%s' % ('[%s] ' % slip.number if slip.number else '', slip.name) for slip in overlapped])
                    raise ValidationError(_("Payslip period for '%s' is overlapped with period(s) of another payslip(s):\n%s.") % (rec.name, overlapped_names))

    def _type_name(self):
        self.ensure_one()
        if self.payment_type == 'advance_salary':
            return _("Salary Advance Slip")
        elif self.payment_type == 'vacations':
            return _("Vacations Slip")
        elif self.payment_type == 'sick_leaves':
            return _("Sick Leaves Slip")
        else:
            return _("Salary Slip")

    @api.depends('wage_type')
    @api.onchange('wage_type')
    def _compute_salary_advance_calculation_editable(self):
        for slip in self:
            slip.salary_advance_calculation_editable = slip.wage_type == 'monthly'

    @api.depends('wage_type')
    @api.onchange('wage_type')
    def _update_salary_advance_calculation(self):
        hourly_advances = self.filtered(lambda slip: slip.payment_type == 'advance_salary' and slip.wage_type == 'hourly')
        if hourly_advances:
            hourly_advances.write({'salary_advance_calculation': 'first_15_days'})

    def _compute_struct_id(self):
        has_structure = self.filtered(lambda rec: rec.struct_id)
        super()._compute_struct_id()
        for slip in has_structure:
            slip.struct_id = slip.contract_id.structure_type_id.default_struct_id

    @api.depends('employee_id', 'struct_id', 'date_from', 'payment_type')
    def _compute_name(self):
        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            lang = slip.employee_id.sudo().address_home_id.lang or self.env.user.lang
            payslip_type = slip._type_name()
            payslip_name = slip.struct_id.payslip_name and '%s: %s' % (slip.struct_id.payslip_name, payslip_type) or payslip_type
            slip.name = '%(payslip_name)s - %(employee_name)s - %(dates)s' % {
                'payslip_name': payslip_name,
                'employee_name': slip.employee_id.name,
                'dates': format_date(self.env, slip.date_from, date_format='MMMM y', lang_code=lang),
            }

    @api.depends('date_to', 'payment_type')
    def _compute_warning_message(self):
        for rec in self:
            if rec.payment_type == 'salary':
                super(HrPayslip, rec)._compute_warning_message()
            else:
                # TODO: process rest of slip types here
                rec.warning_message = False

    @api.depends('average_daily_wage_effective_explanation')
    @api.onchange('average_daily_wage_effective_explanation')
    def _compute_average_daily_wage_effective_explanation_visible(self):
        for rec in self:
            rec.average_daily_wage_effective_explanation_visible = (
                rec.average_daily_wage_effective_explanation
                and rec.average_daily_wage_effective_explanation.strip()
            )

    @api.depends('average_daily_wage')
    @api.onchange('average_daily_wage')
    def _compute_average_daily_wage_effective_visible(self):
        for rec in self:
            decimal_places = rec.currency_id.decimal_places or 2
            rec.average_daily_wage_effective_visible = (
                not float_is_zero(rec.average_daily_wage_effective, precision_digits=decimal_places)
                and float_compare(rec.average_daily_wage, rec.average_daily_wage_effective, precision_digits=decimal_places) != 0
            )

    def _compute_basic_net(self):
        salary_advances = vacations = sick_leaves = salary = self.env['hr.payslip']
        for slip in self:
            if slip.payment_type == 'advance_salary':
                salary_advances |= slip
            elif slip.payment_type == 'vacations':
                vacations |= slip
            elif slip.payment_type == 'sick_leaves':
                sick_leaves |= slip
            else:
                salary |= slip
        line_values = (salary_advances + vacations + sick_leaves)._origin._get_line_values([
            'ADV_GROSS',
            'ADV_NET',
            'VACATIONS_GROSS',
            'VACATIONS_NET',
            'SICK_LEAVES_EMP_GROSS',
            'SICK_LEAVES_CIF_GROSS',
            'SICK_LEAVES_EMP_NET',
            'SICK_LEAVES_CIF_NET',
            'MATERNITY_LEAVES_GROSS',
            'MATERNITY_LEAVES_NET',
        ])
        for payslip in salary_advances:
            payslip.basic_wage = line_values['ADV_GROSS'][payslip._origin.id]['total']
            payslip.net_wage = line_values['ADV_NET'][payslip._origin.id]['total']
        for payslip in vacations:
            payslip.basic_wage = line_values['VACATIONS_GROSS'][payslip._origin.id]['total']
            payslip.net_wage = line_values['VACATIONS_NET'][payslip._origin.id]['total']
        for payslip in sick_leaves:
            if payslip._get_rule_eval_maternity():
                payslip.basic_wage = line_values['MATERNITY_LEAVES_GROSS'][payslip._origin.id]['total']
                payslip.net_wage = line_values['MATERNITY_LEAVES_NET'][payslip._origin.id]['total']
            else:
                payslip.basic_wage = line_values['SICK_LEAVES_EMP_GROSS'][payslip._origin.id]['total'] + line_values['SICK_LEAVES_CIF_GROSS'][payslip._origin.id]['total']
                payslip.net_wage = line_values['SICK_LEAVES_EMP_NET'][payslip._origin.id]['total'] + line_values['SICK_LEAVES_CIF_NET'][payslip._origin.id]['total']
        super(HrPayslip, salary)._compute_basic_net()

    @api.depends('line_ids', 'line_ids.total')
    @api.onchange('line_ids')
    def _compute_lines_deductions(self):
        line_values = self._origin._get_line_values([
            'ADV_PDFO',
            'ADV_MT',
            'ADV_ESV',
            'VACATIONS_PDFO',
            'VACATIONS_MT',
            'VACATIONS_ESV',
            'SICK_LEAVES_EMP_PDFO',
            'SICK_LEAVES_CIF_PDFO',
            'SICK_LEAVES_EMP_MT',
            'SICK_LEAVES_CIF_MT',
            'SICK_LEAVES_EMP_ESV',
            'SICK_LEAVES_CIF_ESV',
            'MATERNITY_LEAVES_PDFO',
            'MATERNITY_LEAVES_MT',
            'MATERNITY_LEAVES_ESV',
            'PDFO',
            'MT',
            'ESV',
        ])
        for payslip in self:
            if payslip.payment_type == 'advance_salary':
                payslip.pdfo_amount = line_values['ADV_PDFO'][payslip._origin.id]['total']
                payslip.mt_amount = line_values['ADV_MT'][payslip._origin.id]['total']
                payslip.esv_amount = line_values['ADV_ESV'][payslip._origin.id]['total']
            elif payslip.payment_type == 'vacations':
                payslip.pdfo_amount = line_values['VACATIONS_PDFO'][payslip._origin.id]['total']
                payslip.mt_amount = line_values['VACATIONS_MT'][payslip._origin.id]['total']
                payslip.esv_amount = line_values['VACATIONS_ESV'][payslip._origin.id]['total']
            elif payslip.payment_type == 'sick_leaves':
                if payslip._get_rule_eval_maternity():
                    payslip.pdfo_amount = line_values['MATERNITY_LEAVES_PDFO'][payslip._origin.id]['total']
                    payslip.mt_amount = line_values['MATERNITY_LEAVES_MT'][payslip._origin.id]['total']
                    payslip.esv_amount = line_values['MATERNITY_LEAVES_ESV'][payslip._origin.id]['total']
                else:
                    payslip.pdfo_amount = line_values['SICK_LEAVES_EMP_PDFO'][payslip._origin.id]['total'] + line_values['SICK_LEAVES_CIF_PDFO'][payslip._origin.id]['total']
                    payslip.mt_amount = line_values['SICK_LEAVES_EMP_MT'][payslip._origin.id]['total'] + line_values['SICK_LEAVES_CIF_MT'][payslip._origin.id]['total']
                    payslip.esv_amount = line_values['SICK_LEAVES_EMP_ESV'][payslip._origin.id]['total'] + line_values['SICK_LEAVES_CIF_ESV'][payslip._origin.id]['total']
            else:
                payslip.pdfo_amount = line_values['PDFO'][payslip._origin.id]['total']
                payslip.mt_amount = line_values['MT'][payslip._origin.id]['total']
                payslip.esv_amount = line_values['ESV'][payslip._origin.id]['total']

    @api.depends(
        'employee_id',
        'employee_id.contract_ids',
        'employee_id.contract_ids.date_start',
        'employee_id.contract_ids.date_end',
        'employee_id.contract_ids.wage',
        'contract_id',
        'employee_id.contract_id.date_start',
        'employee_id.contract_id.date_end',
        'employee_id.contract_id.wage',
        'struct_id',
        'date_from',
        'date_to',
        'payment_type',
        'salary_advance_calculation',
        'average_daily_wage',
        'line_ids',
    )
    def _compute_worked_days_line_ids(self):
        super()._compute_worked_days_line_ids()

    @api.depends('line_ids', 'payment_ids')
    def _compute_payments(self):
        for record in self:
            record.payment_count = len(record.payment_ids)
            record.payment_amount = -sum(record.payment_ids.mapped('amount'))

    def _get_current_period_range(self, benefit):
        self.ensure_one()
        if benefit.schedule_pay == 'monthly':
            date_from = fields.Date.start_of(self.date_to, 'month')
            date_to = fields.Date.end_of(self.date_to, 'month')
        elif benefit.schedule_pay == 'quarterly':
            date_from = fields.Date.start_of(self.date_to, 'quarter')
            date_to = fields.Date.end_of(self.date_to, 'quarter')
        elif benefit.schedule_pay == 'semi-annually':
            year = self.date_to.year
            month = self.date_to.month
            if month <= 6:
                date_from = date(year, 1, 1)
                date_to = date(year, 6, 30)
            else:
                date_from = date(year, 7, 1)
                date_to = date(year, 12, 31)
        else:
            # self.schedule_pay == 'annually'
            date_from = fields.Date.start_of(self.date_to, 'year')
            date_to = fields.Date.end_of(self.date_to, 'year')
        return date_from, date_to

    def _get_previous_period_range(self, benefit, current_range=None):
        self.ensure_one()
        current_range = current_range or self._get_current_period_range(benefit)
        date_from, date_to = current_range
        if benefit.schedule_pay == 'monthly':
            delta = relativedelta(months=1)
        elif benefit.schedule_pay == 'quarterly':
            delta = relativedelta(months=3)
        elif benefit.schedule_pay == 'semi-annually':
            delta = relativedelta(months=6)
        else:
            # self.schedule_pay == 'annually'
            delta = relativedelta(years=1)
        date_from -= delta
        date_to -= delta
        return date_from, date_to

    def _get_period_range(self, benefit):
        current = self._get_current_period_range(benefit)
        if benefit.account_in_next_period:
            result = self._get_previous_period_range(benefit, current)
        else:
            result = current
        return result

    def _match_contract_benefit(self, benefit):
        date_from = self.date_from
        date_to = self.date_to
        if benefit.account_in_next_period:
            date_from = fields.Date.start_of(date_from - relativedelta(months=1), 'month')
            date_to = fields.Date.end_of(date_from, 'month')
        return (
            benefit.date_from <= date_to
            and (not benefit.date_to or benefit.date_to > date_from)
            and (
                benefit.schedule_pay == 'monthly'
                or (benefit.schedule_pay == 'quarterly' and date_to and date_to.month in (3, 6, 9, 12))
                or (benefit.schedule_pay == 'semi-annually' and date_to and date_to.month == 6)
                or (benefit.schedule_pay == 'annually' and date_to and date_to.month == 12)
            )
        )

    @api.depends('contract_id', 'contract_id.payroll_contract_benefit_ids')
    @api.onchange('contract_id')
    def _update_benefit_lines(self):

        def _get_benefit_data(payslip, benefit):
            is_contract_benefit = benefit._name == 'hr.payroll.contract.benefit'
            line_values = {
                'payslip_id': payslip.id or payslip._origin.id,
                'name': benefit.benefit_name if is_contract_benefit else benefit.name,
                'code': benefit.benefit_code if is_contract_benefit else benefit.code,
                'type': benefit.benefit_type if is_contract_benefit else benefit.type,
                'schedule_pay': benefit.schedule_pay or None,
                'mode': 'auto' if is_contract_benefit else 'manual',
                'is_alimony': benefit.is_alimony,
                'charge_type': benefit.charge_type,
                'amount_base': benefit.amount_base,
                'account_debit_id': benefit.account_debit_id and benefit.account_debit_id.id or None,
                'account_credit_id': benefit.account_credit_id and benefit.account_credit_id.id or None,
                'account_in_next_period': benefit.account_in_next_period,
                'receiver_id': benefit.receiver_id and benefit.receiver_id.id or None,
            }
            if benefit.amount_base == 'fixed':
                line_values['fixed_amount'] = benefit.fixed_amount
            elif benefit.amount_base == 'percent':
                line_values['percent'] = benefit.percent
                line_values['base_rule_code'] = benefit.base_rule_code
            elif benefit.amount_base == 'percent_in_wages':
                line_values['percent_in_wages'] = benefit.percent_in_wages
                line_values['base_rule_code'] = benefit.base_rule_code
            if benefit.children_ids:
                line_values['children_ids'] = [
                    Command.create({'children_age': rec.children_age, 'children_number': rec.children_number})
                    for rec in benefit.children_ids
                ]

            return line_values

        for slip in self.filtered(lambda rec: rec.payment_type == 'salary'):
            lines = []
            for contract_benefit in slip.contract_id.payroll_contract_benefit_ids.filtered(lambda rec: self._match_contract_benefit(rec)):
                lines.append(_get_benefit_data(slip, contract_benefit))
            for custom_benefit in slip.benefit_line_ids.filtered(lambda rec: rec.mode == 'manual'):
                lines.append(_get_benefit_data(slip, custom_benefit))
            if slip.id or slip._origin.id:
                slip.benefit_line_ids.unlink()
                if lines:
                    self.env['hr.payslip.benefit.line'].create(lines)
            else:
                slip.benefit_line_ids = [Command.clear()] + [Command.create(data) for data in lines]

    def _check_benefit_lines(self):
        self.ensure_one()
        if self.payment_type == 'salary' and self.contract_id.payroll_contract_benefit_ids:
            contract_benefits = self.contract_id.payroll_contract_benefit_ids.filtered(
                lambda benefit: self._match_contract_benefit(benefit)
            )
            contract_benefits_codes = set([benefit.benefit_code for benefit in contract_benefits if benefit.benefit_code])
            self_automated_codes = self.benefit_line_ids.filtered(lambda benefit: benefit.mode == 'auto').mapped('code')
            if not (
                len(contract_benefits_codes) == len(self_automated_codes)
                and all([code in contract_benefits_codes for code in self_automated_codes])
            ):
                self._update_benefit_lines()
                self.env.flush_all()

    def action_payslip_cancel(self):
        self.mapped('move_id').filtered(lambda x: x.state == 'posted').button_draft()
        super().action_payslip_cancel()
        for slip in self.filtered(lambda rec: rec.payment_type == 'salary'):
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('date_start', '>=', slip.date_from),
                ('date_stop', '<=', slip.date_to),
            ])
            work_entries.write({'state': 'draft'})

    def action_payslip_done(self):
        invalid_payslips = self.filtered(lambda p: p.contract_id and (p.contract_id.date_start > p.date_to or (p.contract_id.date_end and p.contract_id.date_end < p.date_from)))
        if invalid_payslips:
            raise ValidationError(_("The following employees have a contract outside of the payslip period:\n%s", '\n'.join(invalid_payslips.mapped('employee_id.name'))))
        if any(slip.contract_id.state == 'cancel' for slip in self):
            raise ValidationError(_("You cannot validate a payslip on which the contract is cancelled"))
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        # !!! >>> Change 1 !!!
        unbalanced_slips = self.env['hr.payslip']
        for slip in self:
            unbalanced_lines = slip.line_ids.filtered(lambda line: line.account_credit_id and not line.account_debit_id)
            if unbalanced_lines and not (slip.contract_id and slip.contract_id.account_id):
                unbalanced_slips |= slip
        if unbalanced_slips:
            message = '\n'.join(unbalanced_slips.mapped('name'))
            raise UserError(_("The following payslips have lines with credit account set but no debit account:\n%s\nTo properly confirm that payslips you need to set up an account on employee's contract page (Salary Information -> Accounting)") % message)
        # !!! >>> Change 1 !!!
        self.write({'state': 'done'})

        line_values = self._get_line_values(['NET'])

        self.filtered(lambda p: not p.credit_note and line_values['NET'][p.id]['total'] < 0).write({'has_negative_net_to_report': True})
        self.mapped('payslip_run_id').action_close()
        # Validate work entries for regular payslips (exclude end of year bonus, ...)
        # !!! >>> Change 2 !!!
        regular_payslips = self.filtered(
            lambda slip: slip.payment_type == 'salary' and slip.struct_id.type_id.default_struct_id == slip.struct_id,
        )
        # !!! >>> Change 2 !!!
        work_entries = self.env['hr.work.entry']
        for regular_payslip in regular_payslips:
            work_entries |= self.env['hr.work.entry'].search([
                ('date_start', '<=', regular_payslip.date_to),
                ('date_stop', '>=', regular_payslip.date_from),
                ('employee_id', '=', regular_payslip.employee_id.id),
            ])
        if work_entries:
            work_entries.action_validate()

        if self.env.context.get('payslip_generate_pdf'):
            if self.env.context.get('payslip_generate_pdf_direct'):
                self._generate_pdf()
            else:
                self.write({'queued_for_pdf': True})
                payslip_cron = self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs', raise_if_not_found=False)
                if payslip_cron:
                    payslip_cron._trigger()
        self._action_create_account_move()

    def action_create_payments(self):
        # show created bank statement lines
        return self.env['hr.payslip.create_payment'].create_and_show(self)

    def action_show_payments(self):
        self.ensure_one()
        return self.payment_ids.action_show()

    def _action_create_account_move(self):
        to_process = self.filtered(lambda slip: slip.payment_type != 'advance_salary')
        if to_process and to_process.filtered(lambda slip: slip.payslip_run_id):
            # Prevent creating a single move per payslip run
            result = True
            for rec in to_process:
                save_run_id = rec.payslip_run_id
                try:
                    rec.payslip_run_id = False
                    result = super(HrPayslip, rec)._action_create_account_move() and result
                finally:
                    rec.payslip_run_id = save_run_id
        else:
            result = super(HrPayslip, to_process)._action_create_account_move()
        if not config['test_enable'] or self.env.context.get('payslip_test_force_post_move'):
            for rec in to_process.filtered(lambda slip: slip.state == 'done' and slip.move_id and slip.move_id.state == 'draft'):
                rec.move_id.action_post()
        return result

    def _get_employee_partner(self):
        return self.employee_id.address_home_id or None

    def _get_employee_actual_contract(self):
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to)
        return contracts and contracts[0] or None

    def _round(self, value, precision_digits=None):
        return float_round(value, precision_digits=precision_digits or self.currency_id.decimal_places or 2)

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        result = super()._prepare_line_values(line, account_id, date, debit, credit)
        if result:
            account = self.env['account.account'].browse(account_id).exists()
            if account and account.account_type == 'liability_payable':
                if line.benefit_line_id and line.benefit_line_id.is_alimony and line.benefit_line_id.receiver_id:
                    result['partner_id'] = line.benefit_line_id.receiver_id.id
                elif account.code and account.code.startswith('66'):
                    result['partner_id'] = line.partner_id.id or self.employee_id.address_home_id.id or None
        return result

    def _prepare_slip_lines(self, date, line_ids):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []
        for line in self.line_ids.filtered(lambda rec: rec.category_id):
            amount = line.total
            # Check if the line is the 'Net Salary'.
            if line.code == 'NET':
                for tmp_line in self.line_ids.filtered(lambda rec: rec.category_id):
                    # Check if the rule must be computed in the 'Net Salary' or not.
                    if tmp_line.salary_rule_id.not_computed_in_net:
                        if amount > 0:
                            amount -= abs(tmp_line.total)
                        elif amount < 0:
                            amount += abs(tmp_line.total)
            if float_is_zero(amount, precision_digits=precision):
                continue
            # !!! Use line's accounts, not rule's ones !!!
            debit_account_id = line.account_debit_id.id
            credit_account_id = line.account_credit_id.id
            if line.code in ('PDFO', 'MT', 'VACATIONS_PDFO', 'VACATIONS_MT') and amount < 0:
                amount = -amount
            # If the rule has a debit account.
            if debit_account_id:
                debit = amount if amount > 0.0 else 0.0
                credit = -amount if amount < 0.0 else 0.0

                debit_line = self._get_existing_lines(line_ids + new_lines, line, debit_account_id, debit, credit)

                if not debit_line:
                    debit_line = self._prepare_line_values(line, debit_account_id, date, debit, credit)
                    debit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_debit.tax_ids.ids]
                    new_lines.append(debit_line)
                else:
                    debit_line['debit'] += debit
                    debit_line['credit'] += credit

            # If the rule has a credit account.
            if credit_account_id:
                debit = -amount if amount < 0.0 else 0.0
                credit = amount if amount > 0.0 else 0.0
                credit_line = self._get_existing_lines(line_ids + new_lines, line, credit_account_id, debit, credit)

                if not credit_line:
                    credit_line = self._prepare_line_values(line, credit_account_id, date, debit, credit)
                    credit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_credit.tax_ids.ids]
                    new_lines.append(credit_line)
                else:
                    credit_line['debit'] += debit
                    credit_line['credit'] += credit
        return new_lines

    def _get_contract_hours_per_day(self, contract=None, contract_id=None, default_value=HOURS_PER_DAY):
        contract = contract or (contract_id and self.env['hr.contract'].browse(contract_id).exists()) or self.contract_id
        hours_per_day = contract and contract.resource_calendar_id.hours_per_day
        if not hours_per_day or float_is_zero(hours_per_day, precision_digits=2):
            hours_per_day = default_value
        return hours_per_day

    def _get_base_local_dict(self):
        result = super()._get_base_local_dict()
        result.update({
            '_logger': _logger,
            'round': self._round,
            'HAS_ADVANCE_PAYSLIP': self.has_advance_payslip(),
            'MATERNITY_LEAVE': self.is_maternity_leave(),
            'BUSINESS_TRIP_DAYS': self.get_business_trip_days(),
            'DAY_OFF_WORKING_DAYS': self.get_day_off_working_days(),
            'HAS_CHARITY': self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and rec.charge_type == 'charity') and True or False,
            'HAS_BONUS': self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and rec.charge_type == 'bonus') and True or False,
            'HAS_ACCRUALS': self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and not rec.charge_type) and True or False,
            'HAS_ALIMONY': self.benefit_line_ids.filtered(lambda rec: rec.type == 'deduction' and rec.is_alimony) and True or False,
            'HAS_DEDUCTIONS': self.benefit_line_ids.filtered(lambda rec: rec.type == 'deduction' and not rec.is_alimony) and True or False,
            'TIMESHEET_BASED_SALARY': self.is_timesheet_based_salary(),
            'CUMULATIVE_INFLATION_RATES': self._compute_cumulative_inflation_rates(),
        })
        if result.get('TIMESHEET_BASED_SALARY'):
            result['TIMESHEET_PROJECTS'] = self.get_timesheet_projects()
        if self.struct_id and self.struct_id.rule_ids:
            result.update({code: 0.0 for code in self.struct_id.rule_ids.mapped('code')})
        return result

    def _post_process_compute_rule(self, rule, localdict, compute_result):
        if (
            (self.payment_type == 'vacations' and rule.code == 'VACATIONS_GROSS')
            or (self.payment_type == 'sick_leaves' and rule.code in ('SICK_LEAVES_EMP_GROSS', 'MATERNITY_LEAVES_GROSS'))
        ):
            self.average_daily_wage_effective = localdict.get('_average_daily_wage') or self.average_daily_wage
            self.average_daily_wage_effective_explanation = localdict.get('_average_daily_wage_effective_explanation')
        return compute_result

    def _get_work_entries(self, date_from=None, date_to=None, contracts=None, domain=None, inside=True):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        contracts = contracts or self.employee_id._get_contracts(date_from, date_to, states=['open', 'close'])
        return self.env['hr.work.entry'].search(contracts._get_work_hours_domain(date_from, date_to, domain, inside))

    def _count_working_time(self, date_from=None, date_to=None, contracts=None, domain=None, inside=True, calendar_time=False):
        days = hours = 0.0
        work_entries = self._get_work_entries(
            date_from=date_from,
            date_to=date_to,
            contracts=contracts,
            domain=domain,
            inside=inside,
        )
        if work_entries:
            min_date = date_from
            if isinstance(min_date, date):
                min_date = datetime.combine(min_date, time.min)
            max_date = date_to
            if isinstance(max_date, date):
                max_date = datetime.combine(max_date, time.max)

            hours = 0.0
            days = 0.0
            for work_entry in work_entries:
                work_entry_start = max(work_entry.date_start, min_date)
                work_entry_end = min(work_entry.date_stop, max_date)
                if calendar_time:
                    curr_time = self.get_calendar_time(work_entry_start, work_entry_end)
                    hours += (curr_time or {}).get('hours') or 0.0
                    days += (curr_time or {}).get('days') or 0.0
                else:
                    current_hours = (work_entry_end - work_entry_start).total_seconds() / 3600
                    current_days = current_hours / self._get_contract_hours_per_day(work_entry.contract_id)
                    hours += current_hours
                    days += current_days

        return {'days': days, 'hours': hours}

    def _get_new_worked_days_lines(self):
        result = super()._get_new_worked_days_lines()
        if result:
            work_entry_codes = {
                rec['id']: rec['code']
                for rec in self.env['hr.work.entry.type'].search_read([], ['id', 'code'])
            }
            result_filtered = []
            if self.payment_type == 'vacations':
                allowed_codes = {'LEAVE90', 'LEAVE100', 'LEAVE120'}
            elif self.payment_type == 'sick_leaves':
                allowed_codes = {'LEAVE100', 'LEAVE110', 'LEAVE_UA16'}
            else:
                allowed_codes = {'LEAVE100', 'WORK100', 'LEAVE_UA07', 'OUT', 'WORK_UA03', 'WORK_UA04'}
            for rec in result:
                vals = isinstance(rec, (list, tuple)) and len(rec) == 3 and rec[2] or None
                work_entry_type_id = vals and vals.get('work_entry_type_id') or None
                if work_entry_type_id and work_entry_codes[work_entry_type_id] in allowed_codes:
                    result_filtered.append(rec)
            if result_filtered:
                result = result_filtered

        if self.payment_type == 'salary':
            day_off_data = self._get_worked_day_off_data()
            if day_off_data:
                work_entry_type = self.env.ref('selferp_l10n_ua_salary.hr_work_entry_type_work_on_day_off')
                if result is None:
                    result = []
                for (contract_id, date_from, date_to), days_count in day_off_data.items():
                    result += [Command.create({
                        'work_entry_type_id': work_entry_type.id,
                        'contract_id': contract_id,
                        'sequence': work_entry_type.sequence,
                        'number_of_days': days_count,
                        'number_of_hours': days_count * self._get_contract_hours_per_day(contract_id=contract_id),
                    })]
        return result

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        self.ensure_one()
        result = []
        date_from = self.date_from
        date_to = self.date_to
        if self.payment_type == 'advance_salary' and self.salary_advance_calculation == 'first_15_days':
            date_from = fields.Date.start_of(date_from, 'month')
            date_to = date_from + timedelta(days=14)
        contracts = self.employee_id._get_contracts(date_from, date_to, states=['open', 'close'])
        if contracts:
            contracts = contracts.sorted(key=lambda rec: rec.date_start)
            start = max(date_from, contracts[0].date_start)
            max_contract = len(contracts) - 1
            gaps = []
            if start > date_from:
                gaps.append((date_from, start - timedelta(days=1)))
            for i in range(max_contract + 1):
                if contracts[i].resource_calendar_id:
                    if contracts[i].date_end:
                        end = min(date_to, contracts[i].date_end)
                    elif i < max_contract:
                        end = min(date_to, contracts[i + 1].date_start - timedelta(days=1))
                    else:
                        end = date_to
                    context = dict(self.env.context)
                    context.update({
                        'payslip_date_from': start,
                        'payslip_date_to': end,
                        'force_contract': contracts[i],
                    })
                    contract_lines = self.with_context(context)._get_worked_day_lines_values(domain=domain)
                    if contract_lines:
                        for line in contract_lines:
                            line['contract_id'] = contracts[i].id
                        result.extend(contract_lines)
                    if i < max_contract:
                        start = contracts[i + 1].date_start
                        if (start - end).days > 1:
                            gaps.append((end, start - timedelta(days=1)))
                    elif end < date_to:
                        gaps.append((end, date_to))

            if self.payment_type == 'advance_salary':
                work_records = dict()
                # Merge different contracts records to one
                for rec in result:
                    work_entry_type_id = rec['work_entry_type_id']
                    if work_entry_type_id not in work_records:
                        work_records[work_entry_type_id] = rec
                    else:
                        work_records[work_entry_type_id]['number_of_days'] += rec['number_of_days']
                        work_records[work_entry_type_id]['number_of_hours'] += rec['number_of_hours']
                result = list(work_records.values())

            if check_out_of_contract and gaps:
                reference_calendar = self._get_out_of_contract_calendar()
                out_days = out_hours = 0
                for date_from, date_to in gaps:
                    start = datetime.combine(date_from, time.min)
                    stop = datetime.combine(date_to, time.max)
                    work_entry_domain = ['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)]
                    out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=work_entry_domain)
                    out_days += out_time['days']
                    out_hours += out_time['hours']
                if out_days or out_hours:
                    work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                    result.append({
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_days': out_days,
                        'number_of_hours': out_hours,
                    })
        return result

    def _get_leaves_hours(self, date_from, date_to, code, leave_entries):
        result = []
        work_entries = leave_entries.filtered(lambda rec: rec.work_entry_type_id.code == code)
        if work_entries:
            actual_leave = work_entries.mapped('leave_id')
            actual_work_entry_type = work_entries.mapped('work_entry_type_id')
            # The leave's date range must match the slip's one
            if not (
                len(actual_work_entry_type) == 1
                and len(actual_leave) == 1
                and actual_leave.holiday_status_id.work_entry_type_id
                and actual_leave.holiday_status_id.work_entry_type_id.code == code
                and actual_leave.date_from.date() <= date_from
                and actual_leave.date_to.date() >= date_to
            ):
                actual_leave = None
            calendar = self.env.ref('selferp_l10n_ua_salary.resource_calendar_service_56h')
            add_timesheet_codes = self.env.context.get('add_timesheet_codes')
            if actual_leave:
                data = self.employee_id._get_work_days_data_batch(
                    self._localize_date(datetime.combine(date_from, time.min)),
                    self._localize_date(datetime.combine(date_to, time.max)),
                    compute_leaves=False,
                    calendar=calendar,
                )
                time_data = data and data.get(self.employee_id.id) or {}
                if time_data:
                    attendance_line = {
                        'sequence': actual_work_entry_type.sequence,
                        'work_entry_type_id': actual_work_entry_type.id,
                        'number_of_hours': time_data['hours'],
                        'number_of_days': time_data['days'],
                    }
                    if add_timesheet_codes:
                        attendance_line.update({
                            'code': actual_work_entry_type.code,
                            'timesheet_ccode': actual_work_entry_type.timesheet_ccode,
                            'timesheet_ncode': actual_work_entry_type.timesheet_ncode,
                        })
                    result.append(attendance_line)
            else:
                entries_by_leave = defaultdict(lambda: self.env['hr.work.entry'])
                for work_entry in work_entries:
                    entries_by_leave[(work_entry.leave_id, work_entry.work_entry_type_id, work_entry.contract_id)] |= work_entry
                for (leave, work_entry_type, contract), work_entries in entries_by_leave.items():
                    work_entries = work_entries.sorted(key=lambda rec: rec.date_start)
                    days = 0.0
                    hours = 0.0
                    if len(work_entries) == 1 and (work_entries.date_stop - work_entries.date_start).days > 0:
                        # This means that work entry was added manually in the calendar view (on whole leave's range?)
                        start = work_entries[0].date_start
                        stop = work_entries[-1].date_stop
                        contract_start = contract.date_start and datetime.combine(contract.date_start, time.min) or None
                        contract_end = contract.date_end and datetime.combine(contract.date_end, time.min) or None
                        if contract_start and contract_start > start:
                            start = contract_start
                        if contract_end and contract_end < stop:
                            stop = contract_end
                        data = self.employee_id._get_work_days_data_batch(
                            self._localize_date(datetime.combine(start.date(), time.min)),
                            self._localize_date(datetime.combine(stop.date(), time.max)),
                            compute_leaves=False,
                            calendar=calendar,
                        )
                        time_data = data and data.get(self.employee_id.id) or {}
                        if time_data:
                            days = time_data['days']
                            hours = time_data['hours']
                    else:
                        # Fallback to default behaviour
                        max_index = len(work_entries) - 1
                        for i in range(max_index + 1):
                            work_entry = work_entries[i]
                            duration = work_entry.duration
                            hours += duration
                            days += duration / self._get_contract_hours_per_day(contract)
                    attendance_line = {
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_hours': hours,
                        'number_of_days': days,
                    }
                    if add_timesheet_codes:
                        attendance_line.update({
                            'code': work_entry_type.code,
                            'timesheet_ccode': work_entry_type.timesheet_ccode,
                            'timesheet_ncode': work_entry_type.timesheet_ncode,
                        })
                    result.append(attendance_line)
        return result

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        result = []
        date_from = self.date_from
        date_to = self.date_to

        if self.payment_type == 'advance_salary' and self.salary_advance_calculation == 'first_15_days':
            date_from = fields.Date.start_of(date_from, 'month')
            date_to = date_from + timedelta(days=14)

        if self.env.context.get('payslip_date_from'):
            date_from = self.env.context['payslip_date_from']
        if self.env.context.get('payslip_date_to'):
            date_to = self.env.context['payslip_date_to']
        if self.env.context.get('force_contract'):
            contracts = self.env.context['force_contract']
        else:
            contracts = self.employee_id._get_contracts(date_from, date_to, states=['open', 'close']).sorted(key=lambda rec: rec.date_start)
        work_hours = defaultdict(lambda: (0, 0))
        for contract in contracts:
            contract_hours = contract._get_work_hours(
                datetime.combine(date_from, time.min),
                datetime.combine(date_to, time.max),
            )
            for work_entry_type, hours in contract_hours.items():
                total_hours, total_days = work_hours[work_entry_type]
                total_hours += hours
                total_days += hours / self._get_contract_hours_per_day(contract)
                work_hours[work_entry_type] = (total_hours, total_days)
        work_entry_type_ids = list({rec[0] for rec in work_hours.items()})
        HrWorkEntryType = self.env['hr.work.entry.type']
        work_entry_types = {rec.id: rec for rec in HrWorkEntryType.browse(work_entry_type_ids)}
        work_entries = self._get_work_entries(date_from, date_to, contracts=contracts)
        result.extend(self._get_leaves_hours(date_from, date_to, 'LEAVE120', work_entries))
        result.extend(self._get_leaves_hours(date_from, date_to, 'LEAVE_UA16', work_entries))
        result.extend(self._get_leaves_hours(date_from, date_to, 'LEAVE110', work_entries))
        result.extend(self._get_leaves_hours(date_from, date_to, 'LEAVE_UA07', work_entries))
        work_hours = list(filter(
            lambda rec: rec and (work_entry_types.get(rec[0]) or HrWorkEntryType).code not in ('LEAVE110', 'LEAVE_UA16', 'LEAVE120', 'LEAVE_UA07') or False,
            work_hours.items(),
        ))
        work_hours_ordered = sorted(work_hours, key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_timesheet_codes = self.env.context.get('add_timesheet_codes') or False
        add_days_rounding = 0
        for work_entry_type_id, (hours, days) in work_hours_ordered:
            work_entry_type = work_entry_types[work_entry_type_id]
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_hours': hours,
                'number_of_days': day_rounded,
            }
            if add_timesheet_codes:
                attendance_line.update({
                    'code': work_entry_type.code,
                    'timesheet_ccode': work_entry_type.timesheet_ccode,
                    'timesheet_ncode': work_entry_type.timesheet_ncode,
                })
            result.append(attendance_line)
        if result:
            codes = self.env.context.get('work_entry_codes')
            if codes:

                def _match_codes(rec):
                    rec_type = work_entry_types.get(rec.get('work_entry_type_id')) or HrWorkEntryType
                    return rec_type.timesheet_ccode in codes

                result = list(filter(lambda rec: _match_codes(rec), result))
        return result

    def _get_worked_time_records(self, date_from=None, date_to=None, codes=None):
        self.ensure_one()
        if date_from or date_to or codes:
            context = dict(self.env.context)
            if date_from:
                context['payslip_date_from'] = date_from
            if date_to:
                context['payslip_date_to'] = date_to
            if codes:
                context['work_entry_codes'] = codes
            self = self.with_context(**context)
        return self._get_worked_day_lines_values()

    def _is_first_working_day_of_month(self, date, contract=None):
        result = False
        if not contract or contract.date_start > date or (contract.date_end and contract.date_end < date):
            contracts = self.employee_id._get_contracts(
                fields.Date.start_of(date, 'month'),
                fields.Date.end_of(date, 'month'),
                states=['open', 'close'],
            )
            contract = contracts and contracts.sorted(key=lambda rec: rec.date_start)[0] or None
        if contract:
            work_intervals = contract.resource_calendar_id._work_intervals_batch(
                self._localize_date(datetime.combine(fields.Date.start_of(date, 'month'), time.min)),
                self._localize_date(datetime.combine(date - timedelta(days=1), time.max)),
                resources=self.employee_id.resource_id,
            )
            result = not (work_intervals and work_intervals[self.employee_id.resource_id and self.employee_id.resource_id.id or False])
        return result

    def _localize_date(self, dt):
        tz = self.employee_id and self.employee_id.resource_calendar_id and self.employee_id.resource_calendar_id.tz or self.env.user.tz
        if tz:
            return pytz.timezone(tz).localize(dt)
        return pytz.utc.localize(dt)

    def _get_tz(self, contract=None):
        return (contract or (self.employee_id.resource_calendar_id and self.employee_id.resource_calendar_id) or self.env.user).tz

    @api.model
    def _sum_work_time(self, work_time_lines):
        days = hours = 0
        for line in work_time_lines:
            days += line.get('number_of_days') or 0
            hours += line.get('number_of_hours') or 0
        return {
            'days': days,
            'hours': hours,
        }

    def _get_scheduled_work_entries(self, date_from=None, date_to=None):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        date_from = datetime.combine(date_from, datetime.min.time())
        date_to = datetime.combine(date_to, datetime.max.time())
        work_data = defaultdict(lambda: (0, 0))
        employee_contracts = self.employee_id._get_contracts(date_from, date_to, states=['open', 'close'])
        # TODO: check why contract_id._get_work_entries_values() returns records for all contracts !!!
        work_entry_values = self.contract_id._get_work_entries_values(date_from, date_to)
        # work_entry_values = []
        # for contract in self.employee_id._get_contracts(date_from, date_to, states=['open', 'close']):
        #     contract_values = contract._get_work_entries_values(date_from, date_to)
        #     if contract_values:
        #         for values in contract_values:
        #             values['contract'] = contract
        #         work_entry_values.extend(contract_values)
        work_entry_type_ids = {work_entry['work_entry_type_id'] for work_entry in work_entry_values}
        work_entry_types = {rec.id: rec for rec in self.env['hr.work.entry.type'].browse(list(work_entry_type_ids))}
        contracts = {contract.id: contract for contract in employee_contracts}

        contract_dates = {}

        def _add_contract_dates(contract, contract_start, contract_end, data):
            contract_dates[(contract_start, contract_end)] = contract

        self._contracts_operations(_add_contract_dates, employee_contracts, date_from.date(), date_to.date())

        def _find_contract(start, end):
            for (contract_start, contract_end), contract in contract_dates.items():
                if start >= contract_start and end <= contract_end:
                    return contract
            return self.contract_id

        for work_entry in work_entry_values:
            date_start = max(date_from, work_entry['date_start'])
            date_stop = min(date_to, work_entry['date_stop'])
            work_entry_type = work_entry_types.get(work_entry['work_entry_type_id'])
            if work_entry_type:
                total_hours, total_days = work_data[work_entry_type.id]
                if work_entry_type.is_leave:
                    contract = _find_contract(date_start.date(), date_stop.date())
                    calendar = contract.resource_calendar_id
                    employee = contract.employee_id
                    contract_data = employee._get_work_days_data_batch(
                        date_start,
                        date_stop,
                        compute_leaves=False,
                        calendar=calendar,
                    )[employee.id]
                    hours = contract_data.get('hours', 0)
                else:
                    hours = _get_work_duration(date_start, date_stop)
                days = hours / self._get_contract_hours_per_day(contracts[work_entry['contract_id']])
                total_hours += hours
                total_days += days
                work_data[work_entry_type.id] = (total_hours, total_days)

        scheduled_data = [
            {
                'work_entry_type_id': work_entry_type_id,
                'number_of_hours': hours,
                'number_of_days': days,
                'timesheet_ccode': work_entry_types[work_entry_type_id].timesheet_ccode,
                'timesheet_ncode': work_entry_types[work_entry_type_id].timesheet_ncode,
                'is_leave': work_entry_types[work_entry_type_id].is_leave,
                '_type': work_entry_types[work_entry_type_id].name,
            } for work_entry_type_id, (hours, days) in work_data.items()
        ]
        return scheduled_data

    def get_scheduled_time_first_15_days(self):
        self.ensure_one()
        date_from = fields.Date.start_of(self.date_from, 'month')
        date_to = date_from + timedelta(days=14)
        # TODO: check which of work entry types are acceptable
        return self.get_scheduled_time(date_from, date_to, ('Р',))

    def _get_scheduled_time_first_15_days(self):
        date_from = fields.Date.start_of(self.date_from, 'month')
        date_to = date_from + timedelta(days=14)
        return self._get_scheduled_time(date_from, date_to)

    def get_worked_time_first_15_days(self):
        self.ensure_one()
        date_from = fields.Date.start_of(self.date_from, 'month')
        date_to = date_from + timedelta(days=14)
        # TODO: check which of work entry types are acceptable
        return self._sum_work_time(
            self._get_worked_time_records(date_from, date_to, ('Р',)),
        )

    def get_scheduled_time(self, date_from=None, date_to=None, codes=None):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        scheduled_data = self._get_scheduled_work_entries(date_from, date_to)
        if codes:
            # TODO: check which of work entry types are acceptable
            scheduled_data = [rec for rec in scheduled_data if rec.get('timesheet_ccode') in codes]
        return self._sum_work_time(scheduled_data)

    def _get_scheduled_time(self, date_from=None, date_to=None, compute_leaves=False):
        self.ensure_one()
        hours = days = 0.0
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        contracts = self.employee_id._get_contracts(date_from, date_to, ['open', 'close'])
        if contracts:
            contracts = contracts.sorted(lambda rec: rec.date_start)

            def _compute_contract_scheduled_time(contract, contract_start, contract_end, data):
                batch = self.employee_id._get_work_days_data_batch(
                    self._localize_date(datetime.combine(contract_start, time.min)),
                    self._localize_date(datetime.combine(contract_end, time.max)),
                    compute_leaves=compute_leaves,
                    calendar=contract.resource_calendar_id,
                )
                contract_data = batch.get(self.employee_id.id) or {}
                current_hours = contract_data.get('hours', 0)
                current_days = contract_data.get('days', 0)
                data['hours'] += current_hours
                data['days'] += current_days
                if not compute_leaves:
                    leaves_count = self._get_global_leaves_count(contract_start, contract_end, contract.resource_calendar_id)
                    if leaves_count:
                        data['days'] -= leaves_count
                        data['hours'] -= leaves_count * self._get_contract_hours_per_day(contract)

            time_data = self._contracts_operations(
                _compute_contract_scheduled_time,
                contracts,
                date_from,
                date_to,
                defaultdict(float),
                include_out_of_contract=True,
            )
            if time_data:
                hours = time_data.get('hours')
                days = time_data.get('days')

        return {'hours': hours, 'days': days}

    def get_scheduled_time_full_month(self):
        self.ensure_one()
        date_from = fields.Date.start_of(self.date_from, 'month')
        date_to = fields.Date.end_of(date_from, 'month')
        # TODO: check which of work entry types are acceptable
        return self.get_scheduled_time(date_from, date_to, ('Р', 'В'))

    def _get_scheduled_time_full_month(self):
        return self._get_scheduled_time()

    def get_worked_time(self, date_from=None, date_to=None, codes=('Р',)):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        return self._sum_work_time(
            self._get_worked_time_records(date_from, date_to, codes),
        )

    def get_calendar_time(self, date_from=None, date_to=None, calendar=None):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        calendar = calendar or self.env.ref('selferp_l10n_ua_salary.resource_calendar_service_56h')
        data = self.employee_id._get_work_days_data_batch(
            self._localize_date(datetime.combine(date_from, time.min)),
            self._localize_date(datetime.combine(date_to, time.max)),
            compute_leaves=False,
            calendar=calendar,
        )
        duration = data[self.employee_id.id]
        if not duration:
            duration = {'days': 0.0, 'hours': 0.0}
        return duration

    @api.model
    def _get_global_leaves_count(self, date_from, date_to, calendar):
        result = 0
        if date_from and date_to and calendar:
            domain = [
                ('resource_id', '=', False),
                ('calendar_id', '=', calendar.id),
                ('date_from', '>=', fields.Date.to_string(date_from)),
                ('date_to', '<=', fields.Date.to_string(date_to)),
            ]
            global_leaves = self.env['resource.calendar.leaves'].search(domain)
            for leave in global_leaves:
                # TODO: check it (refactor if necessary) !!!
                result += (leave.date_to - leave.date_from).days + 1
        return result

    def get_global_leaves_count(self, date_from=None, date_to=None):
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        # TODO: refactor it for case when employee has different contracts with different resource calendars
        # TODO: what if there are gaps between contracts?
        return self._get_global_leaves_count(date_from, date_to, self.employee_id.resource_calendar_id)

    def get_employee_leaves_count(self, date_from=None, date_to=None):
        self.ensure_one()
        work_entries = self._get_work_entries(
            date_from=date_from,
            date_to=date_to,
            domain=[('work_entry_type_id.code', '=', 'LEAVE100')],
        )
        days = 0
        contract_hours_per_day = {}
        for work_entry in work_entries:
            contract_id = work_entry.contract_id.id
            hors_per_day = contract_hours_per_day.get(contract_id)
            if not hors_per_day:
                contract_hours_per_day[contract_id] = hors_per_day = self._get_contract_hours_per_day(contract_id)
            days += work_entry.duration / hors_per_day
        return days

    def _get_settlement_period(self, payment_types=('salary', 'vacations', 'sick_leaves')):
        self.ensure_one()
        if self.date_from and self.date_to:
            date_to = fields.Date.start_of(self.date_from, 'month') - timedelta(days=1)
            date_from = fields.Date.start_of(date_to - relativedelta(years=1) + timedelta(days=1), 'month')
            contracts = self.employee_id._get_contracts(date_from, date_to, ['open', 'close']).sorted('date_start')
            domain = [
                ('employee_id', '=', self.employee_id.id),
                ('payment_type', 'in', payment_types),
                ('state', 'in', ('paid', 'done')),
                ('date_from', '>=', fields.Date.to_string(date_from)),
                ('date_to', '<=', fields.Date.to_string(date_to)),
            ]
            payslips = self.env['hr.payslip'].search(domain).sorted('date_from')
            return date_from, date_to, contracts, payslips
        return self.date_from, self.date_to, None, None

    def get_average_daily_wage_for_vacations(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'vacations' or self.env.context.get('force_type') == 'vacations':
            if self.average_daily_wage:
                result = self.average_daily_wage
            else:
                date_from, date_to, contracts, payslips = self._get_settlement_period()
                if contracts:
                    first_contract = self.employee_id.get_first_contract()
                    if payslips:
                        calendar_from = fields.Date.start_of(max(payslips[0].date_from, contracts[0].date_start), 'month')
                        calendar_to = min(payslips[-1].date_to, contracts[-1].date_end or date_to)

                        first_contract_date = first_contract.date_start
                        if (
                            first_contract_date.year == calendar_from.year
                            and first_contract_date.month == calendar_from.month
                            and first_contract_date.day > calendar_from.day
                            and not self._is_first_working_day_of_month(first_contract_date, first_contract)
                        ):
                            # Skip month if the employee started working not from the first working day of the month
                            next_month_date = fields.Date.start_of(calendar_from + relativedelta(months=1), 'month')
                            tmp_payslips = payslips.filtered(lambda slip: slip.date_from >= next_month_date)
                            if tmp_payslips and tmp_payslips.filtered(lambda slip: slip.payment_type == 'salary'):
                                payslips = tmp_payslips
                                calendar_from = fields.Date.start_of(max(payslips[0].date_from, payslips[0].contract_id.date_start), 'month')

                        if payslips:
                            gross = sum(payslips.mapped('line_ids').filtered(lambda rec: rec.code in ADW_CODES).mapped('total'))
                            lines_domain = expression.AND([
                                [('slip_id.employee_id', '=', self.employee_id.id)],
                                [('slip_id', 'not in', payslips.ids)],
                                [('slip_id.state', 'in', ('done', 'paid'))],
                                [('benefit_line_id', '!=', False)],
                                expression.OR([
                                    expression.AND([
                                        [('account_date_from', '<=', calendar_from)],
                                        [('account_date_to', '>', calendar_from)],
                                    ]),
                                    expression.AND([
                                        [('account_date_from', '>=', calendar_from)],
                                        [('account_date_to', '<=', calendar_to)],
                                    ]),
                                    expression.AND([
                                        [('account_date_from', '<', calendar_to)],
                                        [('account_date_to', '>=', calendar_to)],
                                    ]),
                                    expression.AND([
                                        [('account_date_from', '<=', calendar_from)],
                                        [('account_date_to', '>=', calendar_to)],
                                    ]),
                                ]),
                            ])
                            another_period_lines = self.env['hr.payslip.line'].search(lines_domain)
                            if another_period_lines:
                                for line in another_period_lines:
                                    months = _months_between_dates(line.account_date_from, line.account_date_to)
                                    if months:
                                        monthly_value = line.amount / months
                                        overlap_start = max(line.account_date_from, calendar_from)
                                        overlap_end = min(line.account_date_to, calendar_to)
                                        if overlap_start < overlap_end:
                                            effective_months = _months_between_dates(overlap_start, overlap_end)
                                            gross += self._round(effective_months * monthly_value)
                            calendar_days = (calendar_to - calendar_from).days + 1
                            if calendar_days:
                                leaves_days = self.get_global_leaves_count(calendar_from, calendar_to)
                                if calendar_days > leaves_days:
                                    result = gross / (calendar_days - leaves_days)
                                    explanation = _("%.2f %s / (%d calendar day(s) - %d holiday(s))") % (gross, self.currency_id.symbol, calendar_days, leaves_days)
                                    self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
        return self._round(result)

    def _get_sick_leave_exclude_days(self, date_from=None, date_to=None):
        # TODO: check and delete this method
        self.ensure_one()
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        # ТН - Тимчасова непрацездатність
        # ВП - Відпустка по вагітності / пологах тa відпустка для догляду за дитинoю до досягнення трирічного віку
        # ДД - Відпустка для дoгляду за дитиною дo досягнення шестирічного віку
        # БЗ - Iнші відпустки бeз збереження зарплати (нa період припинення виконання pобіт)
        # TODO: add another codes for vacations without salary
        exclude_codes = ('ТН', 'ВП', 'ДД', 'БЗ',)
        context = dict(add_timesheet_codes=True, **self.env.context)
        worked_records = self.with_context(context)._get_worked_time_records(date_from, date_to, exclude_codes)
        exclude_days = 0
        for worked_record in worked_records:
            exclude_days += worked_record.get('days') or 0
        return exclude_days

    def _is_unpaid_time_off(self):
        self.ensure_one()
        if self.payment_type == 'vacations':
            unpaid_days = self.worked_days_line_ids.filtered(lambda rec: rec.work_entry_type_id.code == 'LEAVE90')
            return unpaid_days and True or False
        return False

    def _is_worked_full_month(self, date):
        date_from = fields.Date.start_of(date, 'month')
        date_to = fields.Date.end_of(date, 'month')
        scheduled_days = (self._get_scheduled_time(date_from, date_to) or {}).get('days') or 0
        worked_days = (self.get_worked_time(date_from, date_to, ('Р', 'В', 'Н', 'ТН', 'ВП', 'ДД')) or {}).get('days') or 0
        return worked_days >= scheduled_days

    def _get_start_ensurance_experience_date(self):
        if (
            self.employee_id
            and self.employee_id.hire_date
            and (self.employee_id.work_experience_years or self.employee_id.work_experience_months or self.employee_id.work_experience_days)
        ):
            experience_start = self.employee_id.hire_date
            work_experience_years = safe_int(self.employee_id.work_experience_years)
            work_experience_months = safe_int(self.employee_id.work_experience_months)
            work_experience_days = safe_int(self.employee_id.work_experience_days)
            if work_experience_years:
                experience_start -= relativedelta(years=work_experience_years)
            if work_experience_months:
                experience_start -= relativedelta(months=work_experience_months)
            if work_experience_days:
                experience_start -= relativedelta(days=work_experience_days)
            return experience_start
        return None

    def get_average_daily_wage_for_sick_leaves(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'sick_leaves' or self.env.context.get('force_type') == 'sick_leaves':
            maternity_leave = self._get_rule_eval_maternity()
            apply_rate = self._get_employee_sick_leave_rate()
            if maternity_leave:
                apply_rate = 1.0
            if not (apply_rate is None or float_is_zero(apply_rate, precision_digits=2)):
                amount_digits = self.currency_id.decimal_places or 2
                if self.average_daily_wage:
                    self._set_to_rule_eval_data('_average_daily_wage', self.average_daily_wage)
                    result = apply_rate * self.average_daily_wage
                else:
                    first_contract = self.employee_id.get_first_contract()
                    first_contract_date = first_contract.date_start
                    date_from, date_to, contracts, payslips = self._get_settlement_period()
                    work_more_than_year = first_contract.date_start + relativedelta(months=12) <= date_to
                    start_experience_date = self._get_start_ensurance_experience_date()
                    # TODO: ask if wee need to show message when start_experience_date is not defined !!!
                    work_more_than_six_months = start_experience_date and start_experience_date + relativedelta(months=6) <= date_to or False
                    if payslips and contracts:
                        if work_more_than_year:
                            working_from = fields.Date.start_of(max(payslips[0].date_from, contracts[0].date_start), 'month')
                            if (
                                first_contract_date.year == working_from.year
                                and first_contract_date.month == working_from.month
                                and first_contract_date.day > working_from.day
                            ):
                                # Skip month if the employee started working not from the first day of the month
                                next_month_date = fields.Date.start_of(working_from + relativedelta(months=1), 'month')
                                tmp_payslips = payslips.filtered(lambda slip: slip.date_from >= next_month_date)
                                if tmp_payslips and tmp_payslips.filtered(lambda slip: slip.payment_type == 'salary'):
                                    payslips = tmp_payslips
                                else:
                                    payslips = None
                        else:
                            working_from = first_contract_date
                            working_from_payslip = fields.Date.start_of(working_from, 'month')
                            payslips = payslips.filtered(lambda slip: slip.date_from >= working_from_payslip)
                        if payslips:
                            payslip_dates = defaultdict(lambda: self.env['hr.payslip'])
                            vacation_dates = defaultdict(lambda: self.env['hr.payslip'])
                            sick_leave_dates = defaultdict(lambda: self.env['hr.payslip'])
                            unpaid_time_off_dates = defaultdict(lambda: self.env['hr.payslip'])
                            for rec in payslips:
                                date = fields.Date.start_of(rec.date_from, 'month')
                                if rec.payment_type == 'salary':
                                    payslip_dates[date] |= rec
                                elif rec.payment_type == 'vacations':
                                    if rec._is_unpaid_time_off():
                                        unpaid_time_off_dates[date] |= rec
                                    else:
                                        vacation_dates[date] |= rec
                                elif rec.payment_type == 'sick_leaves':
                                    sick_leave_dates[date] |= rec

                            settlement_days = 0
                            settlement_amount = 0
                            all_settlements_days = all_vacations_days = all_unpaid_days = 0
                            for date, payslip in payslip_dates.items():
                                if len(payslip) == 1 and payslip._is_worked_full_month(date):
                                    end_date = fields.Date.end_of(date, 'month')
                                    month_days = (end_date - date).days + 1
                                    settlement_days += month_days
                                    all_settlements_days += month_days
                                    leaves_days = payslip.get_global_leaves_count(date, end_date)
                                    settlement_days -= leaves_days
                                    all_vacations_days += leaves_days
                                    vacations = vacation_dates[date]
                                    sick_leaves = sick_leave_dates[date]
                                    unpaid_time_offs = unpaid_time_off_dates[date]
                                    # TODO: ask what if a vacation covers two months?
                                    for slip_line in (payslip + vacations).mapped('line_ids').filtered(lambda line: line.code in ADW_SICK_LEAVES_CODES):
                                        amount = slip_line.amount
                                        fixed_amount = slip_line.slip_id.fix_esv_base(slip_line.amount)
                                        if amount > fixed_amount:
                                            amount = fixed_amount
                                        settlement_amount += amount
                                    for rec in (sick_leaves + unpaid_time_offs):
                                        unpaid_days = (min(rec.date_to, date_to) - rec.date_from).days + 1
                                        settlement_days -= unpaid_days
                                    if not unpaid_time_offs:
                                        # TODO: check if its possible to make leaves and slips with overlapping dates
                                        unpaid_leaves = self.env['hr.leave'].search([
                                            ('holiday_type', '=', 'employee'),
                                            ('employee_id', '=', self.employee_id.id),
                                            ('payslip_state', '=', 'done'),
                                            ('holiday_status_id.work_entry_type_id.code', '=', 'LEAVE90'),
                                            ('date_from', '>=', date),
                                            ('date_to', '<=', end_date),
                                        ])
                                        for leave in unpaid_leaves:
                                            settlement_days -= leave.number_of_days
                                            all_unpaid_days += leave.number_of_days

                            if settlement_days > 0 and not float_is_zero(settlement_amount, precision_digits=amount_digits):
                                raw_adw = self._round(settlement_amount / settlement_days)
                                self._set_to_rule_eval_data('_average_daily_wage', raw_adw)
                                explanation = _("%.2f %s / (%d calendar day(s) - %d holiday(s) - %d unpaid day(s))") % (settlement_amount, self.currency_id.symbol, all_settlements_days, all_vacations_days, all_unpaid_days)
                                self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
                                result = apply_rate * raw_adw

                    if not payslips and float_is_zero(result, precision_digits=amount_digits) and self.wage_type == 'monthly':
                        # Check: date_from & date_to must contain actual sick leave period, not a sick leave month!
                        worked_time = self.get_worked_time(first_contract_date, self.date_from - timedelta(days=1))
                        worked_days = (worked_time or {}).get('days') or 0
                        if not float_is_zero(worked_days, precision_digits=2):
                            scheduled_time = self._get_scheduled_time(
                                fields.Date.start_of(first_contract_date, 'month'),
                                fields.Date.end_of(first_contract_date, 'month'),
                            )
                            scheduled_days = (scheduled_time or {}).get('days') or 0
                            if not float_is_zero(scheduled_days, precision_digits=2):
                                raw_adw = self._round(first_contract.wage / scheduled_days)
                                explanation = _("1st month: %.2f %s / %d day(s).") % (first_contract.wage, self.currency_id.symbol, scheduled_days)
                                self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
                            else:
                                # Generally this is an impossible situation, so return zero in this case
                                raw_adw = 0.0
                        else:
                            raw_adw = self._round(self.employee_id.contract_id.wage / AVG_DAYS_PER_MONTH)
                            explanation = _("1st day: %.2f %s / %.2f day(s)") % (self.employee_id.contract_id.wage, self.currency_id.symbol, AVG_DAYS_PER_MONTH)
                            self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
                        self._set_to_rule_eval_data('_average_daily_wage', raw_adw)
                        result = apply_rate * raw_adw
                    if not float_is_zero(result, precision_digits=amount_digits) and maternity_leave:
                        min_wage = self.get_minimum_wage()
                        if not float_is_zero(min_wage, precision_digits=amount_digits):
                            raw_adw = self._round(min_wage / AVG_DAYS_PER_MONTH)
                            min_adw = apply_rate * raw_adw
                            if result < min_adw:
                                self._set_to_rule_eval_data('_average_daily_wage', raw_adw)
                                explanation = _("Maternity (less then min. wage): %.2f %s / %.2f day(s)") % (min_wage, self.currency_id.symbol, AVG_DAYS_PER_MONTH)
                                self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
                                result = min_wage
                            elif not work_more_than_six_months:
                                raw_adw = self._round(2 * min_wage / AVG_DAYS_PER_MONTH)
                                max_adw = apply_rate * raw_adw
                                if result > max_adw:
                                    self._set_to_rule_eval_data('_average_daily_wage', raw_adw)
                                    explanation = _("Maternity (less then 6 months): 2 x %.2f %s / %.2f day(s)") % (min_wage, self.currency_id.symbol, AVG_DAYS_PER_MONTH)
                                    self._set_to_rule_eval_data('_average_daily_wage_effective_explanation', explanation)
                                    result = max_adw
        return result

    def _get_employee_sick_leave_rate(self):
        self.ensure_one()
        rates = self.employee_id.sick_leave_rate_ids.filtered(lambda rec: rec.apply_date <= self.date_from).sorted('apply_date')
        return rates and rates[-1].sick_leave_rate_id and rates[-1].sick_leave_rate_id.rate or None

    def _check_employee_sick_leave_rate(self):
        self.ensure_one()
        apply_rate = self._get_employee_sick_leave_rate()
        if not self.is_maternity_leave() and (not apply_rate or float_is_zero(apply_rate, precision_digits=3)):
            date = self.date_from.strftime('%d.%m.%Y')
            raise UserError(_("Please setup sick leave rates on date %s for %s") % (date, self.employee_id.name))

    @api.model
    def _check_vacations(self):
        if not self.env.context.get('check_work_entries', True):
            return
        self.ensure_one()
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        domain = [('work_entry_type_id.code', '=', 'LEAVE120')]
        vacations_entries = self.env['hr.work.entry'].search(
            contracts._get_work_hours_domain(self.date_from, self.date_to, domain))
        if not vacations_entries:
            message = _(
                "There are no work entries of vacations of employee %(employee)s for the period from %(df)s to %(dt)s",
                employee=self.employee_id.name,
                df=self.date_from.strftime('%d.%m.%Y'),
                dt=self.date_to.strftime('%d.%m.%Y'),
            )
            raise UserError(message)

    @api.model
    def _check_sick_leaves(self):
        if not self.env.context.get('check_work_entries', True):
            return
        self.ensure_one()
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        domain = [('work_entry_type_id.code', 'in', ('LEAVE110', 'LEAVE_UA16'))]
        sick_leaves_entries = self.env['hr.work.entry'].search(contracts._get_work_hours_domain(self.date_from, self.date_to, domain))
        if not sick_leaves_entries:
            message = _(
                "There are no work entries of sick leave of employee %(employee)s for the period from %(df)s to %(dt)s",
                employee=self.employee_id.name,
                df=self.date_from.strftime('%d.%m.%Y'),
                dt=self.date_to.strftime('%d.%m.%Y'),
            )
            raise UserError(message)

    def compute_sheet(self):
        for slip in self.filtered(lambda rec: rec.payment_type == 'vacations'):
            slip._check_vacations()
        for slip in self.filtered(lambda rec: rec.payment_type == 'sick_leaves'):
            slip._check_employee_sick_leave_rate()
            slip._check_sick_leaves()
        if not self.env.context.get('payslip_run_id'):
            # See 'hr.payslip.employees' compute_sheet() for details
            work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
            for slip in self:
                if slip.struct_id.type_id.default_struct_id == slip.struct_id:
                    work_entries = self.env['hr.work.entry'].search([
                        ('date_start', '<=', slip.date_to),
                        ('date_stop', '>=', slip.date_from),
                        ('employee_id', '=', slip.employee_id.id),
                        ('state', '!=', 'validated'),
                    ])
                    if work_entries._check_if_error():
                        for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                            work_entries_by_contract[work_entry.contract_id] |= work_entry
            if work_entries_by_contract:
                time_intervals_str = ''
                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str += '\n - '.join(['', *['%s -> %s' % (s[0], s[1]) for s in conflicts._items]]) + '\n'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Some work entries could not be validated."),
                        'message': _("Time intervals to look for:%s", time_intervals_str),
                        'sticky': False,
                    }
                }
        for slip in self.filtered(lambda rec: rec.payment_type == 'salary'):
            slip._check_benefit_lines()
        self.env.flush_all()
        return super().compute_sheet()

    def _get_payslip_lines(self):
        rule_eval_context = {
            'localdict': None,
            'deferred_accruals': dict(),
            'deferred_bonus': dict(),
            'deferred_charity': dict(),
            'deferred_deductions': dict(),
            'deferred_alimony': dict(),
            'deferred_projects': dict(),
            'deferred_projects_esv': dict(),
            'deferred_projects_pdfo': dict(),
            'deferred_projects_mt': dict(),
        }
        self = self.with_context(rule_eval_context=rule_eval_context, **self._context)
        result = super(HrPayslip, self)._get_payslip_lines()
        if result:
            slip_lines = defaultdict(list)
            for line in result:
                slip_lines[line['slip_id']].append(line)

            def _get_line_data(src_data, line_code, line_name, line_amount, account_debit_id=None, account_credit_id=None):
                return {
                    'code': line_code,
                    'name': line_name,
                    'amount': line_amount,
                    'sequence': src_data.get('sequence'),
                    'salary_rule_id': src_data.get('salary_rule_id'),
                    'contract_id': src_data.get('contract_id'),
                    'employee_id': src_data.get('employee_id'),
                    'slip_id': src_data.get('slip_id'),
                    'quantity': src_data.get('quantity'),
                    'rate': src_data.get('rate'),
                    'note': src_data.get('note'),
                    'account_debit_id': account_debit_id or src_data.get('account_debit_id'),
                    'account_credit_id': account_credit_id or src_data.get('account_credit_id'),
                }

            for slip in self:
                if slip.payment_type == 'salary':
                    res_lines = slip_lines.get(slip.id)
                    if not res_lines:
                        continue

                    alimony = list()
                    amount_digits = self.currency_id.decimal_places

                    for key in ('deferred_accruals', 'deferred_bonus', 'deferred_charity', 'deferred_alimony', 'deferred_deductions', 'deferred_projects'):
                        deferred_data = rule_eval_context.get(key)
                        slip_data = deferred_data and deferred_data.get(slip.id) or None
                        if slip_data:
                            for code, lines in slip_data.items():
                                for index in range(len(res_lines)):
                                    res_data = res_lines[index]
                                    if res_data.get('code') == code:
                                        if key != 'deferred_projects':
                                            res_lines.pop(index)
                                        for i in range(len(lines)):
                                            current_line = lines[i]
                                            if key == 'deferred_projects':
                                                project = current_line.get('project')
                                                if project:
                                                    subst_line = _get_line_data(
                                                        res_data,
                                                        'PROJECT_BASIC_%s' % project.id,
                                                        current_line.get('rule_name') or project.name,
                                                        current_line.get('amount') or 0.0,
                                                        current_line.get('account_debit_id'),
                                                        current_line.get('account_credit_id'),
                                                    )
                                                    subst_line['project_id'] = project.id
                                                    res_lines.insert(index + i + 1, subst_line)
                                            else:
                                                benefit_line = current_line.get('benefit_line')
                                                if benefit_line:
                                                    subst_line = _get_line_data(
                                                        res_data,
                                                        benefit_line.code or code,
                                                        current_line.get('rule_name') or benefit_line.name,
                                                        current_line.get('amount') or 0.0,
                                                        current_line.get('account_debit_id'),
                                                        current_line.get('account_credit_id'),
                                                    )
                                                    subst_line['benefit_line_id'] = benefit_line.id
                                                    if key == 'deferred_bonus' and benefit_line.account_in_next_period:
                                                        account_from, account_to = self._get_previous_period_range(benefit_line)
                                                        subst_line.update({
                                                            'account_date_from': account_from,
                                                            'account_date_to': account_to,
                                                        })
                                                    res_lines.insert(index+i, subst_line)
                                                    if key == 'deferred_alimony':
                                                        alimony.append(subst_line)
                                        break

                    def _find_base_amount(base_code):
                        for line_data in res_lines:
                            if line_data.get('code') == base_code:
                                return line_data.get('amount') or 0.0
                        return 0.0

                    def _calc_rule_amount(rule, **kwargs):
                        local_dict = slip._get_localdict()
                        local_dict.update(**kwargs)
                        amount_data = rule._emulate_compute_rule(local_dict)
                        if amount_data:
                            rule_amount, qty, rate = amount_data
                            return rule_amount * qty * rate / 100.0
                        return 0.0

                    def _process_projects(projects, rule_code, tax_rule_code):
                        for index in range(len(res_lines)):
                            res_data = res_lines[index]
                            if res_data.get('code') == rule_code:
                                res_lines.pop(index)
                                for i in range(len(projects)):
                                    project_data = projects[i]
                                    project = project_data.get('project')
                                    if project:
                                        base_amount = _find_base_amount('PROJECT_BASIC_%s' % project.id)
                                        if not float_is_zero(base_amount, precision_digits=amount_digits):
                                            tax_rule = slip.struct_id.rule_ids.filtered(lambda rule: rule.code == tax_rule_code)
                                            amount = tax_rule and _calc_rule_amount(tax_rule, GROSS=base_amount) or 0.0
                                            if not float_is_zero(amount, precision_digits=amount_digits):
                                                subst_line = _get_line_data(
                                                    res_data,
                                                    rule_code,
                                                    project_data.get('rule_name') or '%s - %s' % (project.name, tax_rule_code),
                                                    amount,
                                                )
                                                res_lines.insert(index+i, subst_line)
                                break

                    esv_projects_data = rule_eval_context.get('deferred_projects_esv')
                    projects = esv_projects_data and esv_projects_data.get(slip.id)
                    projects = projects and projects.get('PROJECT_ESV') or None
                    if projects:
                        _process_projects(projects, 'PROJECT_ESV', 'ESV')

                    pdfo_projects_data = rule_eval_context.get('deferred_projects_pdfo')
                    projects = pdfo_projects_data and pdfo_projects_data.get(slip.id)
                    projects = projects and projects.get('PROJECT_PDFO') or None
                    if projects:
                        _process_projects(projects, 'PROJECT_PDFO', 'PDFO')

                    mt_projects_data = rule_eval_context.get('deferred_projects_mt')
                    projects = mt_projects_data and mt_projects_data.get(slip.id)
                    projects = projects and projects.get('PROJECT_MT') or None
                    if projects:
                        _process_projects(projects, 'PROJECT_MT', 'MT')

                    max_result_index = len(res_lines) - 1
                    index = 0

                    if alimony:
                        alimony.reverse()

                    # Some post-processing routines
                    while index <= max_result_index:
                        res_data = res_lines[index]
                        code = res_data.get('code')
                        amount = res_data.get('amount') or 0.0
                        if (
                            code in ('SICK_LEAVES_TECHNICAL', 'VACATIONS_TECHNICAL')
                            and float_is_zero(amount, precision_digits=amount_digits)
                        ):
                            res_lines.pop(index)
                            max_result_index -= 1
                        elif code == 'NET':
                            amount = res_data.get('amount')
                            if amount < 0 and alimony:
                                fixed = False
                                for rec in alimony:
                                    rec_amount = rec.get('amount')
                                    if abs(rec_amount) + amount >= 0:
                                        res_data['amount'] = 0.0
                                        rec['amount'] = rec_amount - amount
                                        fixed = True
                                        break
                                if not fixed:
                                    # TODO: if there are several alimony recipients, then try to distribute the extra amount among all of them
                                    pass
                            index += 1
                        else:
                            index += 1

            fixed_result = list()
            for lines in slip_lines.values():
                fixed_result += (lines or [])
            result = fixed_result

        return result

    def _contracts_operations(self, action, contracts=None, date_from=None, date_to=None, data=None, include_out_of_contract=False):
        self.ensure_one()
        if action and callable(action):
            date_from = date_from or self.date_from
            date_to = date_to or self.date_to
            contracts = contracts or self.employee_id._get_contracts(date_from, date_to)
            if contracts:
                data = data if data is not None else {}
                data.update({
                    'date_from': date_from,
                    'date_to': date_to,
                })

                contracts = contracts.sorted(key=lambda slip: slip.date_start)

                max_contract = len(contracts) - 1
                # contract_start = max(date_from, contracts[0].date_start)
                contract_start = contracts[0].date_start
                if date_from > contract_start or include_out_of_contract:
                    contract_start = date_from
                for i in range(max_contract + 1):
                    if contracts[i].date_end:
                        contract_end = min(date_to, contracts[i].date_end)
                    elif i < max_contract:
                        contract_end = min(date_to, contracts[i + 1].date_start - timedelta(days=1))
                    else:
                        contract_end = date_to
                    action(contracts[i], contract_start, contract_end, data)
                    if i < max_contract:
                        contract_start = contracts[i + 1].date_start
                        # If there is a gap between contracts count it as scheduled days anyway
                        if (contract_start - contract_end).days > 1 and include_out_of_contract:
                            contract_start = contract_end + timedelta(days=1)
        return data

    def adv_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'advance_salary':
            contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
            if contracts:
                contracts = contracts.sorted(key=lambda rec: rec.date_start)
                wage_type = contracts[0].wage_type or self.wage_type
                if wage_type == 'hourly':
                    wage = contracts[0].hourly_wage
                elif wage_type == 'monthly':
                    wage = contracts[0].wage
                else:
                    wage = 0
                worked_f15d_hours = (self.get_worked_time_first_15_days() or {}).get('hours') or 0
                if self.salary_advance_calculation == 'first_15_days':
                    if wage_type == 'hourly':
                        result = wage * worked_f15d_hours
                    elif wage_type == 'monthly':
                        month_scheduled_hours = (self._get_scheduled_time_full_month() or {}).get('hours') or 0
                        if not float_is_zero(month_scheduled_hours, precision_digits=2):
                            result = wage * worked_f15d_hours / month_scheduled_hours
                else:
                    scheduled_f15d_hours = (self._get_scheduled_time_first_15_days() or {}).get('hours') or 0
                    if not float_is_zero(scheduled_f15d_hours, precision_digits=2):
                        result = wage * (self.salary_advance_percents or 0) * worked_f15d_hours / scheduled_f15d_hours
        return self._round(result)

    def _get_business_trip_time(self):
        self.ensure_one()
        days = 0
        hours = 0
        if self.payment_type == 'salary':
            business_trip_domain = [
                ('date_start', '<=', self.date_to),
                ('date_stop', '>=', self.date_from),
                ('employee_id', '=', self.employee_id.id),
                ('work_entry_type_id.code', '=', 'LEAVE_UA07'),
                ('state', 'in', ('draft', 'validated')),
            ]
            work_entries = self.env['hr.work.entry'].search(business_trip_domain)
            manual = work_entries.filtered(lambda rec: not rec.leave_id)
            approved = work_entries - manual

            contract_work_entries = defaultdict(lambda: self.env['hr.work.entry'])
            for work_entry in manual:
                contract_work_entries[work_entry.contract_id] |= work_entry
            for contract, work_entries in contract_work_entries.items():
                contract_hours = sum(work_entries.mapped('duration'))
                hours += contract_hours
                hours_per_day = self._get_contract_hours_per_day(contract)
                days += contract_hours / hours_per_day

            def _compute_leave_duration(current_contract, contract_start, contract_end, init_data):
                if current_contract and contract_start and contract_end:
                    work_hours = current_contract._get_work_hours(
                        datetime.combine(contract_start, time.min),
                        datetime.combine(contract_end, time.max),
                    )
                    if work_hours:
                        current_leave = init_data.get('leave')
                        work_entry_type_id = (
                             current_leave
                             and current_leave.holiday_status_id
                             and current_leave.holiday_status_id.work_entry_type_id
                             and current_leave.holiday_status_id.work_entry_type_id.id
                             or 0
                        )
                        leave_hours = work_entry_type_id and work_hours.get(work_entry_type_id) or 0.0
                        if not _time_is_zero(leave_hours):
                            init_data['hours_count'] = (init_data.get('hours_count') or 0) + leave_hours
                            days_count = leave_hours / self._get_contract_hours_per_day(current_contract) or 0
                            init_data['days_count'] = (init_data.get('days_count') or 0) + days_count

            leaves = approved.mapped('leave_id')
            for leave in leaves:
                leave_from = max(leave.date_from.date(), self.date_from)
                leave_to = min(leave.date_to.date(), self.date_to)
                contracts = self.employee_id._get_contracts(leave_from, leave_to).sorted('date_start')
                if leave.holiday_status_id.in_calendar_days:
                    leave_days = (leave_to - leave_from).days + 1
                    days += leave_days
                    hours += leave_days * self._get_contract_hours_per_day(contract=contracts and contracts[0] or None)
                else:
                    data = self._contracts_operations(
                        _compute_leave_duration,
                        contracts,
                        date_from=leave_from,
                        date_to=leave_to,
                        data={'leave': leave},
                    )
                    days += (data or {}).get('days_count') or 0.0
                    hours += (data or {}).get('hours_count') or 0.0
        return self._round(days, PRECISION_DIGITS_TIME), self._round(hours, PRECISION_DIGITS_TIME)

    def get_business_trip_days(self):
        result = self._get_business_trip_time()
        return result and result[0] or 0.0

    def get_business_trip_hours(self):
        result = self._get_business_trip_time()
        return result and result[1] or 0.0

    def get_business_trip_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            average_daily_salary = expected_daily_salary = 0.0
            first_contract = self.employee_id.get_first_contract()
            first_contract_date = first_contract and first_contract.date_start or None
            if first_contract_date:
                date_end = fields.Date.start_of(self.date_from, 'month') - timedelta(days=1)
                date_start = fields.Date.start_of(date_end - relativedelta(months=1), 'month')
                HrWorkEntries = self.env['hr.work.entry']
                while date_end >= first_contract_date:
                    # TODO: check work entry codes for selecting worked (and paid) time
                    work_entries = HrWorkEntries.search([
                        ('employee_id', '=', self.employee_id.id),
                        ('date_start', '>=', date_start),
                        ('date_stop', '<=', date_end),
                        ('state', 'in', ('draft', 'validated')),
                        ('work_entry_type_id.code', 'not in', ('LEAVE90', 'LEAVE_UA22')),
                    ])
                    if work_entries:
                        break
                    else:
                        date_end = fields.Date.start_of(date_end, 'month') - timedelta(days=1)
                        date_start = fields.Date.start_of(date_end - relativedelta(months=1), 'month')

                if date_end >= first_contract_date:
                    last_payslips = self.env['hr.payslip'].search([
                        ('employee_id', '=', self.employee_id.id),
                        ('payment_type', '=', 'salary'),
                        ('date_from', '>=', date_start),
                        ('date_to', '<=', date_end),
                        ('state', 'in', ('done', 'paid'))
                    ])
                    amount = sum(last_payslips.mapped('line_ids').filtered(lambda line: line.code == 'GROSS').mapped('total'))

                    if not float_is_zero(amount, precision_digits=self.currency_id.decimal_places):
                        contracts = self.employee_id._get_contracts(date_start, date_end, states=['open', 'close'])
                        if contracts:
                            contracts = contracts.sorted(lambda rec: rec.date_start)
                            period_start = max(date_start, contracts[0].date_start)
                            period_end = min(date_end, contracts[-1].date_end or date_end)
                            attendance_id = self.env.ref('hr_work_entry.work_entry_type_attendance').id

                            def _compute_duration(contract, contract_from, contract_to, data):
                                work_hours = contract._get_work_hours(
                                    datetime.combine(contract_from, time.min),
                                    datetime.combine(contract_to, time.max),
                                )
                                days_count = (
                                     work_hours
                                     and (work_hours.get(attendance_id) or 0) / self._get_contract_hours_per_day(contract)
                                     or 0
                                )
                                data['days_count'] = (data.get('days_count') or 0) + days_count

                            work_time = self._contracts_operations(_compute_duration, contracts, period_start, period_end)
                            days = work_time and work_time.get('days_count') or 0
                            if not _time_is_zero(days):
                                average_daily_salary = self._round(amount / days)

                if self.contract_id.wage_type == 'hourly':
                    expected_daily_salary = self.contract_id.hourly_wage * (self.contract_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
                elif self.contract_id.wage_type == 'monthly':
                    amount = self.with_context(business_trip_expected=True, **self.env.context).get_basic_wage()
                    min_wage = self.get_minimum_wage()
                    if float_compare(amount, min_wage, precision_digits=self.currency_id.decimal_places) < 0:
                        amount = min_wage
                    if not float_is_zero(amount, precision_digits=self.currency_id.decimal_places):
                        scheduled_days = (self._get_scheduled_time() or {}).get('days') or 0.0
                        if not _time_is_zero(scheduled_days):
                            expected_daily_salary = self._round(amount / scheduled_days)

                if float_compare(expected_daily_salary, average_daily_salary, precision_digits=self.currency_id.decimal_places) > 0:
                    average_daily_salary = expected_daily_salary
                if not float_is_zero(average_daily_salary, precision_digits=self.currency_id.decimal_places):
                    eval_data = self._get_rule_eval_data()
                    business_trip_days = eval_data and eval_data.get('BUSINESS_TRIP_DAYS') or self.get_business_trip_days()
                    result = average_daily_salary * business_trip_days

        return self._round(result)

    def _get_worked_day_off_data(self, contracts=None):
        contracts = contracts or self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        if contracts:
            EXCLUDE_CODES = ('LEAVE90', 'LEAVE110', 'LEAVE120', 'LEAVE_UA11', 'LEAVE_UA09', 'LEAVE_UA16', 'LEAVE_UA22')

            def _process_contract_day_offs(contract, contract_start, contract_end, data):
                scheduled_time = self._get_scheduled_time(date_from=contract_start, date_to=contract_end)
                if scheduled_time:
                    scheduled_days = (scheduled_time or {}).get('days') or 0.0

                    exclude_time = self._count_working_time(
                        date_from=contract_start,
                        date_to=contract_end,
                        domain=[('work_entry_type_id.code', 'in', EXCLUDE_CODES)],
                        calendar_time=True,
                    )
                    exclude_days = (exclude_time or {}).get('days') or 0.0

                    day_off_time = self._count_working_time(
                        date_from=contract_start,
                        date_to=contract_end,
                        domain=[('work_entry_type_id.code', '=', 'WORK_UA06')],
                    )
                    day_off_days = (day_off_time or {}).get('days') or 0.0

                    working_time = self.get_worked_time(
                        date_from=contract_start,
                        date_to=contract_end,
                        codes=('Р', 'ВД'),
                    )
                    working_days = (working_time or {}).get('days') or 0.0

                    if not _time_is_zero(day_off_days):
                        overtime = working_days + exclude_days + day_off_days - scheduled_days
                        if float_compare(overtime, 0, precision_digits=PRECISION_DIGITS_TIME) > 0:
                            data['work_day_off'][(contract.id, contract_start, contract_end)] = overtime

            day_off_data = self._contracts_operations(
                _process_contract_day_offs,
                contracts=contracts,
                include_out_of_contract=True,
                data={'work_day_off': {}},
            )
            return day_off_data and day_off_data.get('work_day_off') or {}

        return {}

    def get_day_off_working_days(self):
        self.ensure_one()
        result = 0
        if self.payment_type == 'salary':
            day_off_data = self._get_worked_day_off_data()
            if day_off_data:
                return sum(day_off_data.values())
        return result

    def get_work_on_day_off_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
            if contracts:
                day_off_data = self._get_worked_day_off_data(contracts)
                if day_off_data:
                    slip_scheduled_time = self._get_scheduled_time() or {}
                    slip_scheduled_days = slip_scheduled_time.get('days') or 0.0
                    contracts_index = {rec.id: rec for rec in contracts}
                    for (contract_id, date_from, date_to), days_count in day_off_data.items():
                        contract = contracts_index[contract_id]
                        amount = 0.0
                        if contract.wage_type == 'hourly':
                            amount = 2 * days_count * (contract.hourly_wage or 0.0) * self._get_contract_hours_per_day(contract)
                        elif contract.wage_type == 'monthly':
                            scheduled_time = self._get_scheduled_time(date_from=date_from, date_to=date_to) or {}
                            scheduled_days = scheduled_time.get('days') or 0.0
                            if not _time_is_zero(slip_scheduled_days):
                                wage = (contract.wage or 0.0) * scheduled_days / slip_scheduled_days
                                amount = 2 * days_count * wage / scheduled_days
                        result += self._round(amount)
        return result

    def _get_overtime_salary(self, work_entry_type_code):
        self.ensure_one()
        result = 0.0
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        if contracts:
            contracts = contracts.sorted(key=lambda rec: rec.date_start)

            slip_scheduled_hours = (self._get_scheduled_time() or {}).get('hours') or 0.0

            def _process_contract(contract, contract_from, contract_to, data):
                work_entries = self._get_work_entries(
                    date_from=contract_from,
                    date_to=contract_to,
                    contracts=contract,
                    domain=[('work_entry_type_id.code', '=', work_entry_type_code)],
                )
                if work_entries:
                    rate = 1.0
                    work_entry_type = work_entries[0].work_entry_type_id
                    if work_entry_type and work_entry_type.overtime and work_entry_type.surcharge_percents:
                        rate += work_entry_type.surcharge_percents

                    hours_count = work_entries and sum(work_entries.mapped('duration')) or 0.0
                    if contract.wage_type == 'hourly':
                        hourly_wage = contract.hourly_wage or 0.0
                    elif contract.wage_type == 'monthly' and not _time_is_zero(slip_scheduled_hours):
                        hourly_wage = (contract.wage or 0.0) / slip_scheduled_hours
                    else:
                        hourly_wage = 0.0

                    data['overtime_salary'] += rate * hours_count * hourly_wage

            salary_data = self._contracts_operations(_process_contract, contracts, data=defaultdict(float), include_out_of_contract=True)
            result = (salary_data or {}).get('overtime_salary') or 0.0

        return self._round(result)

    def has_evening_working_hours(self):
        self.ensure_one()
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', self.date_from),
            ('date_stop', '<=', self.date_to),
            ('state', 'in', ('draft', 'validated')),
            ('work_entry_type_id.code', '=', 'WORK_UA03'),
        ])
        return work_entries and True or False

    def get_evening_work_salary(self):
        return self._get_overtime_salary('WORK_UA03')

    def has_night_working_hours(self):
        self.ensure_one()
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', self.date_from),
            ('date_stop', '<=', self.date_to),
            ('state', 'in', ('draft', 'validated')),
            ('work_entry_type_id.code', '=', 'WORK_UA04'),
        ])
        return work_entries and True or False

    def get_night_work_salary(self):
        return self._get_overtime_salary('WORK_UA04')

    def _get_indexation_base_date(self):
        self.ensure_one()
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close']).sorted('date_start')
        base_date = (contracts and contracts[0].date_start) or (self.contract_id and self.contract_id.date_start) or None
        if base_date:
            base_date = fields.Date.start_of(base_date, 'month')
            company_id = (self.company_id and self.company_id.id) or (self.employee_id.company_id and self.employee_id.company_id.id) or self.env.company.id
            indexation_period = self.env['salary.indexation_period'].search([('company_id', '=', company_id)])
            if indexation_period:
                acceptable_date = fields.Date.start_of(self.date_from, 'month') - relativedelta(months=2)
                indexation_period = indexation_period.filtered(lambda rec: rec.date_from <= acceptable_date and (not rec.date_to or rec.date_to >= acceptable_date))
                if indexation_period:
                    indexation_period = indexation_period[0]
                    period_date = fields.Date.start_of(indexation_period.date_from, 'month')
                    if period_date > base_date:
                        base_date = period_date - relativedelta(months=1)
                else:
                    base_date = None
        return base_date

    def _compute_cumulative_inflation_rates(self):
        self.ensure_one()
        result = defaultdict(lambda: 1.0)
        base_date = self._get_indexation_base_date()

        if base_date:
            start_date = fields.Date.start_of(base_date, 'month')
            end_date = fields.Date.start_of(self.date_from, 'month')
            if start_date < end_date:
                domain = [('date', '>=', start_date), ('date', '<', end_date)]
                inflation_index = self.env['hr.salary.inflation_index'].search(domain, order='date')
                if inflation_index:
                    inflation_index = {fields.Date.start_of(idx.date, 'month'): idx.value or 1.0 for idx in inflation_index}
                    result[start_date] = 1.0
                    start_date += relativedelta(months=1)
                    current_date = start_date
                    actual_rate = 1.0
                    cumulative_rate = 1.0

                    cumulative_rates = [1.0]

                    def _compute_rate():
                        rate = 1.0
                        if cumulative_rates:
                            for i in range(1, len(cumulative_rates)):
                                rate *= cumulative_rates[i]
                        return rate

                    while current_date < end_date:
                        current_rate = inflation_index.get(current_date) or 1.0
                        cumulative_rate *= current_rate
                        if float_compare(cumulative_rate, ACCEPT_RATE_LIMIT, precision_digits=PRECISION_DIGITS_RATE) > 0:
                            cumulative_rates.append(float_round(cumulative_rate, precision_digits=PRECISION_DIGITS_RATE))
                            actual_rate = float_round(_compute_rate(), precision_digits=PRECISION_DIGITS_RATE)
                            cumulative_rate = 1.0
                        result[current_date] = actual_rate

                        current_date += relativedelta(months=1)
        return result

    def is_indexation_needed(self, cumulative_rates=None):
        self.ensure_one()
        result = False
        if self.payment_type == 'salary':
            max_acceptable_date = fields.Date.start_of(self.date_from - relativedelta(months=2), 'month')
            base_date = self._get_indexation_base_date()
            if base_date and base_date <= max_acceptable_date:
                cumulative_rates = (
                    cumulative_rates
                    or self._get_from_rule_eval_data('CUMULATIVE_INFLATION_RATES')
                    or self._compute_cumulative_inflation_rates()
                )
                if cumulative_rates:
                    dates = sorted(list(cumulative_rates.keys()))

                    for current_date in dates:
                        if current_date > max_acceptable_date:
                            break
                        if float_compare(cumulative_rates[current_date], ACCEPT_RATE_LIMIT, precision_digits=PRECISION_DIGITS_RATE) > 0:
                            result = True
                            break
        return result

    def get_salary_indexation(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            cumulative_rates = (
                self._get_from_rule_eval_data('CUMULATIVE_INFLATION_RATES')
                or self._compute_cumulative_inflation_rates()
            )
            if cumulative_rates and self.is_indexation_needed(cumulative_rates=cumulative_rates):
                actual_date = fields.Date.start_of(self.date_from - relativedelta(months=2), 'month')
                rate = cumulative_rates.get(actual_date)
                if float_compare(rate, ACCEPT_RATE_LIMIT, precision_digits=PRECISION_DIGITS_RATE) > 0:
                    cost_of_living = self.get_cost_of_living()
                    if cost_of_living:
                        adult, from6_to18, under6 = cost_of_living
                        if not float_is_zero(adult, precision_digits=self.currency_id.decimal_places):
                            actual_rate = float_round(rate - 1, precision_digits=PRECISION_DIGITS_RATE)
                            indexation = self._round(adult * actual_rate)
                            contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close']).sorted('date_start')
                            if not contracts:
                                contracts = self.contract_id
                            indexation_salary_changing_month = (
                                contracts
                                and contracts[0].date_end
                                and self.date_from < contracts[0].date_end < self.date_to
                                and contracts[0].date_start < self.date_from - relativedelta(months=2)
                            )
                            salary_change_date = indexation_salary_changing_month and contracts[0].date_end or None
                            scheduled_hours = (self._get_scheduled_time() or {}).get('hours') or 0.0
                            if not _time_is_zero(scheduled_hours):
                                if self.env.context.get('business_trip_expected'):
                                    worked_hours = scheduled_hours
                                else:
                                    worked_hours = (self.get_worked_time(self.date_from, salary_change_date or self.date_to) or {}).get('hours') or 0
                                result = indexation * worked_hours / scheduled_hours
        return self._round(result)

    def _get_basic_wage_general(self):
        self.ensure_one()
        wage = 0.0
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        if contracts:
            contracts = contracts.sorted(key=lambda rec: rec.date_start)
            scheduled_hours = (self._get_scheduled_time() or {}).get('hours') or 0.0

            def _compute_wage(contract, contract_from, contract_to, data):
                if self.env.context.get('business_trip_expected'):
                    worked_hours = (self._get_scheduled_time(contract_from, contract_to) or {}).get('hours') or 0
                else:
                    worked_hours = (self.get_worked_time(contract_from, contract_to) or {}).get('hours') or 0
                wage_type = contract.wage_type or self.wage_type
                if wage_type == 'hourly':
                    data['wage'] += self._round(contract.hourly_wage * worked_hours)
                elif wage_type == 'monthly' and not _time_is_zero(scheduled_hours):
                    data['wage'] += self._round(contract.wage * worked_hours / scheduled_hours)

            wage_data = self._contracts_operations(_compute_wage, contracts, self.date_from, self.date_to, defaultdict(float))
            if wage_data:
                wage = wage_data.get('wage') or 0.0

        return self._round(wage)

    def _get_basic_wage_by_timesheet(self):
        self.ensure_one()
        wage = 0.0
        contracts = self.employee_id._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        if contracts:
            contracts = contracts.sorted(key=lambda rec: rec.date_start)

            def _find_contract(timesheet_date):
                for current_contract in contracts:
                    if current_contract.date_start <= timesheet_date <= (current_contract.date_end or self.date_to):
                        return current_contract
                return None

            all_lines = self.get_timesheet_data()
            if all_lines:
                projects = list()

                project_lines = defaultdict(lambda: self.env['account.analytic.line'])
                for line in all_lines:
                    project_lines[line.project_id] |= line
                total_amount = 0.0
                for project, lines in project_lines.items():
                    project_hours = 0.0
                    project_amount = 0.0
                    for line in lines.sorted(key=lambda rec: rec.date):
                        contract = _find_contract(line.date)
                        if contract:
                            project_hours += line.unit_amount
                            project_amount += line.unit_amount * contract.hourly_wage
                    total_amount += project_amount

                    projects.append({
                        'project': project,
                        'hours': project_hours,
                        'amount': project_amount,
                    })
                if not float_is_zero(total_amount, precision_digits=self.currency_id.decimal_places):
                    for project_data in projects:
                        project_data['rate'] = (project_data.get('amount') or 0.0) / total_amount

                wage = total_amount
                if projects:
                    rule_eval_context = self._context.get('rule_eval_context')
                    eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
                    rule = eval_data and eval_data.get('current_rule') or None
                    if rule:
                        self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_projects', projects)

        return wage

    def get_basic_wage(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            if self.is_timesheet_based_salary():
                result = self._get_basic_wage_by_timesheet()
            else:
                result = self._get_basic_wage_general()
        return result

    def get_minimum_wage(self, wage_date=None, scheduled_hours=None, force_monthly=False):
        wage_date = wage_date or self.date_from
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ('open', 'close')),
            ('date_start', '<=', wage_date),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', wage_date),
        ])
        contract = contract and contract[0] or None
        if contract:
            minimum_wage = self.env['hr.salary.minimum_wage'].search([('date', '<=', wage_date)], order='date desc', limit=1)
            if minimum_wage:
                if contract.wage_type == 'monthly' or force_monthly:
                    return minimum_wage.value_monthly or 0.0
                elif contract.wage_type == 'hourly':
                    scheduled_hours = scheduled_hours or (self._get_scheduled_time() or {}).get('hours') or 0.0
                    return minimum_wage.value_hourly * scheduled_hours or 0.0
        return 0.0

    def get_cost_of_living(self, current_date=None):
        if not current_date:
            current_date = self.date_from
        domain = [
            ('date', '<=', fields.Date.to_string(current_date)),
        ]
        record = self.env['hr.salary.cost_of_living'].search(domain, order='date desc', limit=1)
        return (
            record
            and (record.value or 0.0, record.value_children_from_6_to_18 or 0.0, record.value_children_under_6 or 0.0)
            or None
        )

    def is_supplement_to_min_wage_needed(self):
        self.ensure_one()
        wage = self.get_basic_wage()
        minimum_wage = self.get_minimum_wage(force_monthly=True)
        scheduled_hours = (self._get_scheduled_time() or {}).get('hours') or 0.0
        worked_hours = (self.get_worked_time() or {}).get('hours') or 0.0

        if _time_is_zero(scheduled_hours):
            return False

        eval_data = self._get_rule_eval_data()

        indexation = eval_data and eval_data.get('SALARY_INDEXATION') or 0.0

        business_trip_hours = self.get_business_trip_hours()

        if not _time_is_zero(business_trip_hours):
            minimum_wage = minimum_wage * (scheduled_hours - business_trip_hours) / scheduled_hours
        else:
            minimum_wage = minimum_wage * worked_hours / scheduled_hours

        amount_digits = self.currency_id.decimal_places or 2
        if float_compare(wage + indexation, minimum_wage, precision_rounding=amount_digits) < 0:
            if (
                self.employee_id.employment_type != 'employment_main_place'
                or self.contract_id.wage_type == 'hourly'
                or self.employee_id.has_actual_disability_group(self.date_from)
            ):
                return False

            contracts = self.employee_id.contract_ids.filtered(lambda rec: rec.state in ('open', 'close')).sorted(key=lambda rec: rec.date_start)

            def _is_hired_not_from_start_of_month():
                if contracts and self.contract_id == contracts[0]:
                    month_of_contract = fields.Date.start_of(contracts[0].date_start, 'month')
                    month_of_payslip = fields.Date.start_of(self.date_from, 'month')
                    return month_of_payslip == month_of_contract and contracts[0].date_start > month_of_payslip
                return False

            def _is_worked_not_to_end_of_month():
                if contracts and self.contract_id == contracts[-1]:
                    month_of_contract = fields.Date.end_of(contracts[-1].date_end, 'month') if contracts[-1].date_end else datetime.max
                    month_of_payslip = fields.Date.end_of(self.date_to, 'month')
                    return month_of_payslip == month_of_contract and (contracts[-1].date_end or datetime.max) < month_of_payslip
                return False

            if _is_hired_not_from_start_of_month() or _is_worked_not_to_end_of_month():
                return False
            return True
        return False

    def get_supplement_to_min_wage(self):
        self.ensure_one()
        if self.is_supplement_to_min_wage_needed():
            wage = self.get_basic_wage()
            minimum_wage = self.get_minimum_wage(force_monthly=True)
            eval_data = self._get_rule_eval_data()
            business_trip_days = eval_data and eval_data.get('BUSINESS_TRIP_DAYS') or self.get_business_trip_days()
            scheduled_days = (self._get_scheduled_time(self.date_from, self.date_to) or {}).get('days') or 0
            if not _time_is_zero(scheduled_days):
                if not _time_is_zero(business_trip_days):
                    minimum_wage = minimum_wage * (scheduled_days - business_trip_days) / scheduled_days
                else:
                    worked_days = (self.get_worked_time(self.date_from, self.date_to) or {}).get('days') or 0
                    minimum_wage = minimum_wage * worked_days / scheduled_days
                indexation = eval_data and eval_data.get('SALARY_INDEXATION') or 0.0
                return self._round(minimum_wage - wage - indexation)
        return 0.0

    def is_tax_social_benefit_needed(self):
        self.ensure_one()
        tax_social_benefit = self.get_tax_social_benefit()
        amount_digits = self.currency_id.decimal_places or 2
        if not float_is_zero(tax_social_benefit, precision_digits=amount_digits):
            return True
        return False

    def get_tax_social_benefit(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary' and self.employee_id.employment_type == 'employment_main_place':
            benefit_record = self.employee_id.get_tax_social_benefit(self.date_from, self.date_to)
            if benefit_record:
                if (
                    len(benefit_record) > 1
                    and not all([benefit.on_children and benefit.tax_social_benefit_code_id.code in ('02', '04') for benefit in benefit_record])
                ):
                    raise UserError(_("Its only one personal tax social benefit record allowed (or more then one for children)"))
                rate_precision = PRECISION_TAX_SOCIAL_BENEFIT_RATE[1]
                wage = self.get_basic_wage()
                cost_of_living = self.get_cost_of_living()
                cost_of_living = cost_of_living and cost_of_living[0] or 0.0
                benefit_base_code = self.env['hr.employee.tax_social_benefit.code'].search([('code', '=', '01')], limit=1)
                benefit_base = (
                    benefit_base_code
                    and not float_is_zero(benefit_base_code.rate, precision_digits=rate_precision)
                    and benefit_base_code.rate * cost_of_living
                    or None
                )
                if benefit_base:
                    wage_limit = float_round(cost_of_living * 1.4, precision_rounding=10.0)
                    if len(benefit_record) == 1 and not benefit_record.on_children:
                        if benefit_record.tax_social_benefit_code_id.code in ('01', '04'):
                            result = benefit_base
                        elif not float_is_zero(benefit_record.tax_social_benefit_code_id.rate, precision_digits=rate_precision):
                            result = benefit_base * benefit_record.tax_social_benefit_code_id.rate
                    else:
                        benefit_codes = {
                            benefit.tax_social_benefit_code_id.code: benefit.tax_social_benefit_code_id
                            for benefit in benefit_record
                            if benefit.tax_social_benefit_code_id.code in ('02', '04')
                        }
                        children = defaultdict(int)
                        for benefit in benefit_record:
                            children[benefit.tax_social_benefit_code_id.code] += benefit.children_qty or 0
                        total_qty = 0
                        for benefit in benefit_record:
                            benefit_code = benefit_codes[benefit.tax_social_benefit_code_id.code]
                            qty = children.get(benefit_code.code) or 0
                            if qty and not float_is_zero(benefit_code.rate, precision_digits=rate_precision):
                                result += benefit_base * qty * benefit_code.rate
                                total_qty += qty
                        if total_qty:
                            wage_limit *= total_qty
                    amount_digits = self.currency_id.decimal_places or 2
                    if float_compare(wage, wage_limit, precision_digits=amount_digits) > 0:
                        return 0.0
        return result

    def fix_esv_base(self, amount):
        self.ensure_one()
        result = 0.0
        scheduled_days = (self._get_scheduled_time(self.date_from, self.date_to) or {}).get('days') or 0
        if scheduled_days > 0:
            result = amount
            minimum_base = self.get_minimum_wage(force_monthly=True)
            maximum_base = 15 * minimum_base
            amount_digits = self.currency_id.decimal_places or 2
            if not float_is_zero(minimum_base, precision_digits=amount_digits) and float_compare(result, minimum_base, precision_digits=amount_digits) < 0:
                result = minimum_base
            elif not float_is_zero(maximum_base, precision_digits=amount_digits) and float_compare(result, maximum_base, precision_digits=amount_digits) > 0:
                result = maximum_base
        return self._round(result)

    def is_sick_leaves_cif_applicable(self):
        self.ensure_one()
        if self.payment_type == 'sick_leaves':
            vacation_time = self.get_worked_time(codes=('ТН',))
            vacation_days = vacation_time and vacation_time.get('days') or 0
            return vacation_days > 5
        return False

    def find_related_payslips(self, payment_type, limit=None):
        self.ensure_one()
        Payslip = self.env['hr.payslip']
        if self.employee_id and self.date_from and self.date_to:
            date_from = fields.Date.start_of(self.date_from, 'month')
            date_to = fields.Date.end_of(self.date_to, 'month')
            domain = [
                ('employee_id', '=', self.employee_id.id),
                ('payment_type', '=', payment_type),
                ('state', 'in', ('done', 'paid')),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
            ]
            if not isinstance(self.id, models.NewId):
                domain += [('id', '!=', self.id)]
            return Payslip.search(domain, limit=limit)
        return Payslip

    def has_advance_payslip(self):
        return self.payment_type == 'salary' and bool(self.find_related_payslips('advance_salary'))

    def is_maternity_leave(self):
        if self.payment_type == 'sick_leaves':
            work_entries = self._get_work_entries()
            codes = work_entries and work_entries.mapped('work_entry_type_id.timesheet_ccode') or None
            return codes and any([code in ('ВП', 'ДД') for code in codes]) or False
        return False

    def is_timesheet_based_salary(self):
        return (
            self.payment_type == 'salary'
            and self.contract_id
            and self.contract_id.wage_type == 'hourly'
            and self.contract_id.timesheet_based_salary
            or False
        )

    def get_timesheet_data(self):
        self.ensure_one()
        return self.env['account.analytic.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_id', '=', False),
            ('global_leave_id', '=', False),
        ])

    def get_timesheet_projects(self):
        self.ensure_one()
        timesheet_data = self.get_timesheet_data()
        projects = timesheet_data and timesheet_data.mapped('project_id')
        if projects:
            return [project for project in projects]
        return None

    def adv_paid(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('advance_salary', limit=1)
            if related_payslips:
                result = sum(related_payslips[0].line_ids.filtered(lambda rec: rec.code == 'ADV_NET').mapped('total'))
        return self._round(result)

    def adv_esv(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('advance_salary', limit=1)
            if related_payslips:
                result = sum(related_payslips[0].line_ids.filtered(lambda rec: rec.code == 'ADV_ESV').mapped('total'))
        return self._round(result)

    def adv_pdfo(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('advance_salary', limit=1)
            if related_payslips:
                result = sum(related_payslips[0].line_ids.filtered(lambda rec: rec.code == 'ADV_PDFO').mapped('total'))
        return self._round(result)

    def adv_mt(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('advance_salary', limit=1)
            if related_payslips:
                result = sum(related_payslips[0].line_ids.filtered(lambda rec: rec.code == 'ADV_MT').mapped('total'))
        return self._round(result)

    def vacations_paid(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('vacations')
            if related_payslips:
                result = sum(related_payslips.mapped('line_ids').filtered(lambda rec: rec.code == 'VACATIONS_NET').mapped('total'))
        return self._round(result)

    def vacations_esv(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('vacations')
            if related_payslips:
                result = sum(related_payslips.mapped('line_ids').filtered(lambda rec: rec.code == 'VACATIONS_ESV').mapped('total'))
        return self._round(result)

    def vacations_pdfo(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('vacations')
            if related_payslips:
                result = sum(related_payslips.mapped('line_ids').filtered(lambda rec: rec.code == 'VACATIONS_PDFO').mapped('total'))
        return self._round(result)

    def vacations_mt(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            # TODO: what if there are more than one related payslips?
            related_payslips = self.find_related_payslips('vacations')
            if related_payslips:
                result = sum(related_payslips.mapped('line_ids').filtered(lambda rec: rec.code == 'VACATIONS_MT').mapped('total'))
        return self._round(result)

    def vacations_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'vacations':
            adw = self.get_average_daily_wage_for_vacations()
            amount_digits = self.currency_id.decimal_places or 2
            if not float_is_zero(adw, precision_digits=amount_digits):
                self._set_to_rule_eval_data('_average_daily_wage', adw)
            vacation_time = self.get_worked_time(codes=('В',))
            vacation_days = vacation_time and vacation_time.get('days') or 0
            if adw and vacation_days:
                result = adw * vacation_days
        return self._round(result)

    def _get_rule_eval_data(self):
        eval_context = self.env.context.get('rule_eval_context')
        return eval_context and eval_context.get('localdict') or None

    def _get_from_rule_eval_data(self, key, default=None):
        if key:
            eval_data = self._get_rule_eval_data()
            return eval_data and key and eval_data.get(key) or default
        return default

    def _set_to_rule_eval_data(self, key, value):
        if key:
            eval_data = self._get_rule_eval_data()
            if eval_data:
                eval_data[key] = value

    def _get_rule_eval_maternity(self):
        return self._get_from_rule_eval_data('MATERNITY_LEAVE') or self.is_maternity_leave()

    def sick_leaves_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'sick_leaves' and not self._get_rule_eval_maternity():
            adw = self.get_average_daily_wage_for_sick_leaves()
            sick_leave_time = self.get_worked_time(codes=('ТН',))
            sick_leave_days = sick_leave_time and sick_leave_time.get('days') or 0
            if adw and sick_leave_days:
                if sick_leave_days > 5:
                    sick_leave_days = 5
                result = adw * sick_leave_days
        return self._round(result)

    def sick_leaves_salary_cif(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'sick_leaves' and not self._get_rule_eval_maternity():
            adw = self.get_average_daily_wage_for_sick_leaves()
            sick_leave_time = self.get_worked_time(codes=('ТН',))
            sick_leave_days = sick_leave_time and sick_leave_time.get('days') or 0
            if adw and sick_leave_days:
                if sick_leave_days > 5:
                    sick_leave_days -= 5
                result = adw * sick_leave_days
        return self._round(result)

    def maternity_salary(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'sick_leaves' and self._get_rule_eval_maternity():
            adw = self.get_average_daily_wage_for_sick_leaves()
            maternity_leave_time = self.get_worked_time(codes=('ВП', 'ДД'))
            maternity_leave_days = maternity_leave_time and maternity_leave_time.get('days') or 0
            if adw and maternity_leave_days:
                result = adw * maternity_leave_days
        return self._round(result)

    def add_projects_esv(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary' and self.is_timesheet_based_salary():
            rule_eval_context = self._context.get('rule_eval_context')
            if rule_eval_context:
                projects = self._get_from_rule_eval_data('TIMESHEET_PROJECTS') or self.get_timesheet_projects()
                if projects:
                    projects = [
                        {
                            'project': project,
                            'rule_name': _("%s - ESV", project.name),
                        } for project in projects
                    ]
                    eval_data = rule_eval_context.get('localdict') or None
                    rule = eval_data and eval_data.get('current_rule') or None
                    if rule:
                        self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_projects_esv', projects)
        return result

    def add_projects_pdfo(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary' and self.is_timesheet_based_salary():
            rule_eval_context = self._context.get('rule_eval_context')
            if rule_eval_context:
                projects = self._get_from_rule_eval_data('TIMESHEET_PROJECTS') or self.get_timesheet_projects()
                if projects:
                    projects = [
                        {
                            'project': project,
                            'rule_name': _("%s - PDFO", project.name),
                        } for project in projects
                    ]
                    eval_data = rule_eval_context.get('localdict') or None
                    rule = eval_data and eval_data.get('current_rule') or None
                    if rule:
                        self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_projects_pdfo', projects)
        return result

    def add_projects_mt(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary' and self.is_timesheet_based_salary():
            rule_eval_context = self._context.get('rule_eval_context')
            if rule_eval_context:
                projects = self._get_from_rule_eval_data('TIMESHEET_PROJECTS') or self.get_timesheet_projects()
                if projects:
                    projects = [
                        {
                            'project': project,
                            'rule_name': _("%s - MT", project.name),
                        } for project in projects
                    ]
                    eval_data = rule_eval_context.get('localdict') or None
                    rule = eval_data and eval_data.get('current_rule') or None
                    if rule:
                        self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_projects_mt', projects)
        return result

    def _save_deferred_lines(self, rule_code, eval_context, key, lines):
        deferred_lines = eval_context.get(key)
        if deferred_lines is None:
            deferred_lines = dict()
            eval_context[key] = deferred_lines
        slip_data = deferred_lines.get(self.id)
        if not slip_data:
            slip_data = dict()
            deferred_lines[self.id] = slip_data
        slip_data[rule_code] = lines

    @staticmethod
    def _update_eval_data_with_deferred_values(eval_data, lines):
        if eval_data and lines:
            for line in lines:
                code = line.get('code')
                if code:
                    eval_data[code] = (eval_data.get(code) or 0.0) + (line.get('amount') or 0.0)

    def get_charity_taxable(self):
        self.ensure_one()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            charity_amount = eval_data and eval_data.get('CHARITY') or 0.0
            precision = self.currency_id.decimal_places
            if not float_is_zero(charity_amount, precision_digits=precision):
                cost_of_living = self.get_cost_of_living()
                if cost_of_living:
                    adult, from6_to18, under6 = cost_of_living
                    min_untaxable_amount = float_round(adult * 1.4, precision_rounding=10)
                    if not float_is_zero(min_untaxable_amount, precision_digits=precision) and charity_amount > min_untaxable_amount:
                        result = self._round(charity_amount - min_untaxable_amount)
        return result

    def add_charity(self):
        self.ensure_one()
        charity = list()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            benefit = self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and rec.charge_type == 'charity')
            if benefit:
                if len(benefit) > 1:
                    # TODO: temporary fix - show error message
                    benefit = benefit[0]
                wage = 0.0
                if benefit.amount_base in ('percent', 'percent_in_wages'):
                    base_rule_code = benefit.base_rule_code or 'BASIC'
                    wage = eval_data and eval_data.get(base_rule_code) or 0.0
                amount = self._round(benefit._compute_amount(wage))
                charity.append({
                    'benefit_line': benefit,
                    'amount': amount,
                })
                result = amount
                self._update_eval_data_with_deferred_values(eval_data, charity)
                rule = eval_data and eval_data.get('current_rule') or None
                if rule:
                    self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_charity', charity)
        return result

    def add_bonus(self):
        self.ensure_one()
        bonus = list()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            for benefit in self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and rec.charge_type == 'bonus'):
                wage = 0.0
                if benefit.amount_base in ('percent', 'percent_in_wages'):
                    base_rule_code = benefit.base_rule_code or 'BASIC'
                    wage = eval_data and eval_data.get(base_rule_code) or 0.0
                amount = self._round(benefit._compute_amount(wage))
                bonus.append({
                    'benefit_line': benefit,
                    'amount': amount,
                })
            result = sum([acc.get('amount') or 0.0 for acc in bonus])
            self._update_eval_data_with_deferred_values(eval_data, bonus)
            rule = eval_data and eval_data.get('current_rule') or None
            if rule:
                self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_bonus', bonus)
        return result

    def add_accruals(self):
        self.ensure_one()
        accruals = list()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            for benefit in self.benefit_line_ids.filtered(lambda rec: rec.type == 'accrual' and not rec.charge_type):
                wage = 0.0
                if benefit.amount_base in ('percent', 'percent_in_wages'):
                    base_rule_code = benefit.base_rule_code or 'BASIC'
                    wage = eval_data and eval_data.get(base_rule_code) or 0.0
                amount = self._round(benefit._compute_amount(wage))
                accruals.append({
                    'benefit_line': benefit,
                    'amount': amount,
                })
            result = sum([acc.get('amount') or 0.0 for acc in accruals])
            self._update_eval_data_with_deferred_values(eval_data, accruals)
            rule = eval_data and eval_data.get('current_rule') or None
            if rule:
                self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_accruals', accruals)
        return result

    def get_sick_leaves_technical(self):
        self.ensure_one()
        result = 0.0
        sick_leaves = self.find_related_payslips('sick_leaves')
        if sick_leaves:
            sick_leaves = sick_leaves.filtered(lambda slip: not slip.is_maternity_leave())
            if sick_leaves:
                lines = sick_leaves.mapped('line_ids').filtered(lambda line: line.code in ('SICK_LEAVES_EMP_NET', 'SICK_LEAVES_CIF_NET'))
                result = sum(lines.mapped('total'))
                # TODO: recompute result if sick leave is bigger then PS's period of it covers only a part of PS's period
        return result

    def get_vacations_technical(self):
        self.ensure_one()
        result = 0.0
        vacations = self.find_related_payslips('vacations')
        if vacations:
            lines = vacations.mapped('line_ids').filtered(lambda line: line.code == 'VACATIONS_NET')
            result = sum(lines.mapped('total'))
            # TODO: recompute result if sick leave is bigger then PS's period of it covers only a part of PS's period
        return result

    def add_alimony(self):
        self.ensure_one()
        alimony = list()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            rule = eval_data and eval_data.get('current_rule') or None
            for benefit in self.benefit_line_ids.filtered(lambda rec: rec.type == 'deduction' and rec.is_alimony):
                wage = 0.0
                if benefit.amount_base in ('percent', 'percent_in_wages'):
                    base_rule_code = benefit.base_rule_code or 'NET_TECHNICAL'
                    wage = eval_data and eval_data.get(base_rule_code) or 0.0
                amount = self._round(benefit._compute_amount(wage))
                cost_of_living = self.get_cost_of_living()
                if cost_of_living:
                    adult, from6_to18, under6 = cost_of_living
                    if benefit.children_ids:
                        min_amount = max_amount = 0.0
                        for children in benefit.children_ids:
                            children_count = children.children_number or 1
                            curr_min = curr_max = 0.0
                            if children.children_age == 'under_6':
                                curr_min = children_count * under6 / 2
                                curr_max = children_count * under6 * 10
                            elif children.children_age == 'from_6_to_18':
                                curr_min = children_count * from6_to18 / 2
                                curr_max = children_count * from6_to18 * 10
                            elif children.children_age == 'from_18_to_23':
                                curr_min = children_count * adult / 2
                                curr_max = children_count * adult * 10
                            min_amount += curr_min
                            max_amount += curr_max

                        dp = self.currency_id.decimal_places
                        if not float_is_zero(min_amount, precision_digits=dp) and amount < min_amount:
                            amount = min_amount
                        if not float_is_zero(max_amount, precision_digits=dp) and amount > max_amount:
                            amount = max_amount
                    # TODO: also add checking for min and max alimony's value according to number of children
                alimony.append({
                    'rule_name': _("Alimony: %s") % benefit.receiver_id.name,
                    'partner_id': benefit.receiver_id.id,
                    'benefit_line': benefit,
                    'amount': -amount,
                })
            result = sum([al.get('amount') or 0.0 for al in alimony])
            self._update_eval_data_with_deferred_values(eval_data, alimony)
            if rule:
                self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_alimony', alimony)
        return result

    def add_deductions(self):
        self.ensure_one()
        deductions = list()
        result = 0.0
        if self.payment_type == 'salary':
            rule_eval_context = self._context.get('rule_eval_context')
            eval_data = rule_eval_context and rule_eval_context.get('localdict') or None
            for benefit in self.benefit_line_ids.filtered(lambda rec: rec.type == 'deduction' and not rec.is_alimony):
                wage = 0.0
                if benefit.amount_base in ('percent', 'percent_in_wages'):
                    base_rule_code = benefit.base_rule_code or 'NET_TECHNICAL'
                    wage = eval_data and eval_data.get(base_rule_code) or 0.0
                amount = self._round(benefit._compute_amount(wage))
                deductions.append({
                    'benefit_line': benefit,
                    'amount': -amount,
                })
            result = sum([ded.get('amount') or 0.0 for ded in deductions])
            self._update_eval_data_with_deferred_values(eval_data, deductions)
            rule = eval_data and eval_data.get('current_rule') or None
            if rule:
                self._save_deferred_lines(rule.code, rule_eval_context, 'deferred_deductions', deductions)
        return result

    def _get_line_total_by_code(self, code):
        self.ensure_one()
        return sum(self.line_ids.filtered(lambda line: line.code == code).mapped('total'))
