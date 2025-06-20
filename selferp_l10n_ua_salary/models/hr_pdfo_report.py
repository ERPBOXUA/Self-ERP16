import calendar

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.exceptions import UserError

from odoo.addons.selferp_l10n_ua_ext.models.account_editable_report import sum_amount_float, count_unique, sum_amount_float_by_condition, count_unique_condition, to_float


DOCS = tuple([
    'J0500109',
    'J0510109M1',
    'J0510109M2',
    'J0510109M3',
    'J0510209',
    'J0510309',
    'J0510409M1',
    'J0510409M2',
    'J0510409M3',
    'J0510509',
    'J0510609',
])


def format_empty_cop(value):
    if value == 0 or value == 0.0:
        return ''
    else:
        return f'{value:15.2f}'


def format_empty_int(value):
    if value == 0 or value == 0.0:
        return ''
    else:
        return f'{int(value):d}'


def sum_amount_format_empty_cop(table, tag):
    return format_empty_cop(sum_amount_float(table, tag))


def sum_amount_by_condition_format_empty_cop(table, tag, condition):
    return format_empty_cop(sum_amount_float_by_condition(table, tag, condition))


def count_unique_format_empty_cop(table, tag):
    return format_empty_cop(count_unique(table, tag))


def count_unique_condition_format_empty_cop(table, tag, condition):
    return format_empty_cop(count_unique_condition(table, tag, condition))


def _get_year_selection(self):
    return [(str(i), str(i)) for i in range(fields.Date.today().year - 2, fields.Date.today().year + 5)]


class HrPDFOReport(models.Model):
    _name = 'hr.pdfo.report'
    _inherit = 'account.editable.report'
    _description = "ESV PDFO Report"

    report_year = fields.Selection(
        selection=_get_year_selection,
        string="Report year",
        default=lambda self: str(fields.Date.today().year),
    )

    report_quarter = fields.Selection(
        selection=[
            ('1', "First quarter"),
            ('2', "Second quarter"),
            ('3', "Third quarter"),
            ('4', "Fourth quarter"),
        ],
        string="Report quarter",
    )

    rendered_html_part_J0500109 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510109M1 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510109M2 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510109M3 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510209 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510309 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510409M1 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510409M2 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510409M3 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510509 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    rendered_html_part_J0510609 = fields.Html(
        compute='_compute_rendered_html_parts'
    )

    include_J0510109M1 = fields.Boolean(default=True)
    include_J0510109M2 = fields.Boolean(default=True)
    include_J0510109M3 = fields.Boolean(default=True)
    include_J0510209 = fields.Boolean(default=False)
    include_J0510309 = fields.Boolean(default=False)
    include_J0510409M1 = fields.Boolean(default=True)
    include_J0510409M2 = fields.Boolean(default=True)
    include_J0510409M3 = fields.Boolean(default=True)
    include_J0510509 = fields.Boolean(default=False)
    include_J0510609 = fields.Boolean(default=False)

    report_type = fields.Selection(
        selection=[
            ('HZ', "Normal"),
            ('HZN', "New"),
            ('HZU', "Clarifying"),
            ('HZD', "Reference"),
        ],
        string="Report type",
        default='HZ',
    )

    @api.onchange('report_year', 'report_quarter')
    def change_period(self):
        if self.report_year and self.report_quarter:
            month_from = (int(self.report_quarter) - 1) * 3 + 1
            month_to = month_from + 2
            year = int(self.report_year)
            self.date_from = date(year, month_from, 1)
            self.date_to = date(year, month_to, calendar.monthrange(year, month_to)[1])

    @api.model
    def _get_editable_report_sequence(self, vals):
        company_id = vals.get('company_id')
        if company_id:
            company = self.env['res.company'].browse(company_id) or self.env.company
        if company.sequence_pdfo_report_id:
            return company.sequence_pdfo_report_id
        else:
            return None     # should never happen

    @api.model
    def _get_part_names(self):
        return DOCS

    @api.model
    def _get_doc_name(self, part_name):
        index = part_name.find('M')
        if index > 0:
            part_name = part_name[:index]
        return part_name

    def _get_doc_num(self, part_name):
        result = super()._get_doc_num(part_name)

        # return number of appendix
        doc_name = self._get_doc_name(part_name)
        if doc_name != part_name:
            result = part_name[len(doc_name) + 1:]

        return result

    @api.model
    def _get_part_action_name(self, part_name):
        part_name = self._get_doc_name(part_name)
        return f'selferp_l10n_ua_salary.hr_salary_esv_pdfo_report_action_{part_name}'

    @api.model
    def _get_part_report_name(self, part_name):
        part_name = self._get_doc_name(part_name)
        return f'selferp_l10n_ua_salary.hr_salary_esv_pdfo_report_template_content_{part_name}'

    # -------------------------------------------------------------------------
    # GENERATE INITIAL DATA
    # -------------------------------------------------------------------------

    def _get_dates_per_month(self):
        date_from = self.date_from
        from_1 = date_from
        to_1 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month)[1])
        from_2 = date_from.replace(day=1, month=date_from.month + 1)
        to_2 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 1)[1], month=date_from.month + 1)
        from_3 = date_from.replace(day=1, month=date_from.month + 2)
        to_3 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 2)[1], month=date_from.month + 2)
        return (from_1, to_1), (from_2, to_2), (from_3, to_3)

    def _generate_data(self):

        def _gen_13_14(date_from, date_to):
            val_13 = 0.0
            val_14 = 0.0
            for payslip in self.env['hr.payslip'].search([
                ('payment_type', '=', 'sick_leaves'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id.id', '=', self.company_id.id),
                ('state', 'in', ('done', 'paid')),
            ]):
                val_13 += payslip._get_line_total_by_code('SICK_LEAVES_EMP_GROSS')
                val_14 += payslip._get_line_total_by_code('SICK_LEAVES_CIF_GROSS')
            return val_13, val_14

        self.ensure_one()

        # define params
        self.date_generate = fields.Datetime.now()

        dates = self._get_dates_per_month()

        HrOrder = self.env['hr.order']
        recruitment = self.env.ref('selferp_l10n_ua_salary.hr_order_type_recruitment')
        recruitments1 = HrOrder.search_count([
            ('type_id', '=', recruitment.id),
            ('order_date', '>=', dates[0][0]),
            ('order_date', '<=', dates[0][1]),
        ])
        recruitments2 = HrOrder.search_count([
            ('type_id', '=', recruitment.id),
            ('order_date', '>=', dates[1][0]),
            ('order_date', '<=', dates[1][1]),
        ])
        recruitments3 = HrOrder.search_count([
            ('type_id', '=', recruitment.id),
            ('order_date', '>=', dates[2][0]),
            ('order_date', '<=', dates[2][1]),
        ])

        values = {
            'HZ': self.report_type,
            'HTIN': self.company_id.company_registry,
            'HNUM': '1',
            #'HKATOTTG': self.company_id.
            'HLOC': ', '.join([
                a.strip()
                for a in (self.company_id.partner_id._display_address(without_company=True) or '').split('\n')
                if a.strip()
            ]),
            'HTEL': self.company_id.phone or '',
            'HEMAIL': self.company_id.email or '',
            'HZIP': self.company_id.zip or '',
            'HSTI': self.company_id.tax_inspection_id and self.company_id.tax_inspection_id.name or '',

            'R061G3': '',       # fill inside _check_included_in_values
            'R061G4': '',       # fill inside _check_included_in_values
            'R062G3': '',       # fill inside _check_included_in_values
            'R062G4': '',       # fill inside _check_included_in_values
            'R063G3': '',       # fill inside _check_included_in_values
            'R063G4': '',       # fill inside _check_included_in_values
            'R064G3': '',       # fill inside _check_included_in_values
            'R064G4': '',       # fill inside _check_included_in_values
            'R065G3': '',       # fill inside _check_included_in_values
            'R065G4': '',       # fill inside _check_included_in_values
            'R066G3': '',       # fill inside _check_included_in_values
            'R066G4': '',       # fill inside _check_included_in_values

            'R091G3': 'X',
            'R110G3': recruitments1,
            'R110G4': recruitments2,
            'R110G5': recruitments3,

            'HZY': self.report_year,
            'HZM': self.date_to.strftime('%m'),
            'HZKV': self.report_quarter,

            'HNAME': self.company_id.name,
            'HDDVG': '',
            'HNDVG': '',
            'HNPDV': self.company_id.vat,
            'HKATOTTG': self.company_id.code_kotauu or '',
            'HKVED': self.company_id.code_kved or '',
            'R08G3': self.company_id.code_kprv or '',

            'HFILL': self.date_generate.strftime('%d.%m.%Y'),
            'HBOS': self.company_id.director_id and self.company_id.director_id.name or '',
            'HKBOS': self.company_id.director_id and self.company_id.director_id.vat or '',
            'HBUH': self.company_id.chief_accountant_id and self.company_id.chief_accountant_id.name or '',
            'HKBUH': self.company_id.chief_accountant_id and self.company_id.chief_accountant_id.vat or '',
        }

        # set doc number for each part
        for doc in DOCS[1:]:
            values[doc + '_HNUM1'] = self._get_doc_num(doc)


        date_from = self.date_from

        from_1 = date_from
        to_1 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month)[1])
        from_2 = date_from.replace(day=1, month=date_from.month + 1)
        to_2 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 1)[1], month=date_from.month + 1)
        from_3 = date_from.replace(day=1, month=date_from.month + 2)
        to_3 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 2)[1], month=date_from.month + 2)

        m1_val13, m1_val14 = _gen_13_14(from_1, to_1)
        values['R01013G3'] = format_empty_cop(m1_val13)
        values['R01014G3'] = format_empty_cop(m1_val14)

        m2_val13, m2_val14 = _gen_13_14(from_2, to_2)
        values['R01013G4'] = format_empty_cop(m2_val13)
        values['R01014G4'] = format_empty_cop(m2_val14)

        m3_val13, m3_val14 = _gen_13_14(from_3, to_3)
        values['R01013G5'] = format_empty_cop(m3_val13)
        values['R01014G5'] = format_empty_cop(m3_val14)

        # generate appendixes
        values.update(self._generate_data_addon1(self.date_from, self.date_to))
        values.update(self._generate_data_addon4(self.date_from, self.date_to))

        return values

    def _generate_data_addon1(self, date_from, date_to):
        from_1 = date_from
        to_1 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month)[1])
        from_2 = date_from.replace(day=1, month=date_from.month + 1)
        to_2 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 1)[1], month=date_from.month + 1)
        from_3 = date_from.replace(day=1, month=date_from.month + 2)
        to_3 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 2)[1], month=date_from.month + 2)

        values = {
            'J0510109M1_T1RXXXX': self._generate_data_addon1_table(from_1, to_1),
            'J0510109M2_T1RXXXX': self._generate_data_addon1_table(from_2, to_2),
            'J0510109M3_T1RXXXX': self._generate_data_addon1_table(from_3, to_3),
            'J0510109M1_HNM': 1,
            'J0510109M2_HNM': 2,
            'J0510109M3_HNM': 3,
        }
        return values

    def _generate_data_addon1_table(self, date_from, date_to):

        def mater_period(payslip, period):
            if payslip.date_from > period[0]:
                mater_from = payslip.date_from
            else:
                mater_from = period[0]

            if payslip.date_to < period[1]:
                mater_to = payslip.date_to
            else:
                mater_to = period[1]
            return mater_from, mater_to

        def get_column_14(payslip):
            hire_orders = self.env['hr.order'].search([
                ('date_of_employment', '>=', date_from),
                ('date_of_employment', '<=', date_to),
                ('employee_id', '=', payslip.employee_id.id),
            ])
            if hire_orders:
                hire_date = hire_orders[0].date_of_employment
                return format_empty_int((date_to - hire_date).days + 1)
            else:
                return format_empty_int((date_to - date_from).days + 1)

        def fill_bage(payslip):
            return {
                'T1RXXXXG5': 1,  # TODO add field
                'T1RXXXXG6': 'Ч' if payslip.employee_id.gender == 'male' else 'Ж' if payslip.employee_id.gender == 'female' else None,
                'T1RXXXXG7S': payslip.employee_id.address_home_id.vat if payslip.employee_id.address_home_id else '',
                'T1RXXXXG8': 2 if payslip.employee_id.has_actual_disability_group(date_from) else 1,
                'T1RXXXXG9': '',
                'T1RXXXXG101': date_from.month,
                'T1RXXXXG102': date_from.year,
                'T1RXXXXG111S': payslip.employee_id.last_name,
                'T1RXXXXG112S': payslip.employee_id.first_name,
                'T1RXXXXG113S': payslip.employee_id.patronymic,
                'T1RXXXXG12': '',
                'T1RXXXXG13': '',
                'T1RXXXXG14': '',
                'T1RXXXXG15': '',
                'T1RXXXXG16': '',
                'T1RXXXXG17': '',
                'T1RXXXXG18': '',
                'T1RXXXXG19': '',
                'T1RXXXXG20': '',
                'T1RXXXXG21': 1 if payslip.employee_id.is_labor_book else 0,
                'T1RXXXXG23': 0,
                'T1RXXXXG24': 0,
                'T1RXXXXG22': 0,
                'T1RXXXXG25': '',
                'T1RXXXXG26': 1 if payslip.contract_id.non_fixed_working_hours else 0,
            }

        def fill_by_general(payslip):
            t1rxxxxg16 = payslip._get_line_total_by_code('GROSS')
            min_wage = payslip.get_minimum_wage(wage_date=date_from)
            #t1rxxxxg12 = format_empty_cop(payslip.get_worked_time(date_from, date_to, ('ТН',)).get('days'))
            t1rxxxxg12 = ''
            t1rxxxxg13 = format_empty_cop(payslip.get_worked_time(date_from, date_to, ('НБ', 'ДБ', 'НА', 'БЗ')).get('days'))
            # TODO: rewrite in case many hiring and firing per month
            t1rxxxxg14 = ''
            t1rxxxxg15 = ''

            values = fill_bage(payslip)
            values.update({
                'T1RXXXXG12': t1rxxxxg12,
                'T1RXXXXG13': t1rxxxxg13,
                'T1RXXXXG14': t1rxxxxg14,
                'T1RXXXXG15': t1rxxxxg15,
                'T1RXXXXG16': format_empty_cop(t1rxxxxg16),
                'T1RXXXXG17': format_empty_cop(t1rxxxxg16 if t1rxxxxg16 < 15 * min_wage or not min_wage else 15 * min_wage),
                'T1RXXXXG20': format_empty_cop(payslip._get_line_total_by_code('ESV')),
            })
            return values

        HrPayslip = self.env['hr.payslip']
        values = []
        salary_persons = set()
        for payslip in HrPayslip.search([
            ('payment_type', '=', 'salary'),
            ('date_from', '>=', date_from),
            ('date_from', '<=', date_to),
            ('company_id.id', '=', self.company_id.id),
            ('state', 'in', ('done', 'paid')),
        ]):
            if payslip.employee_id.address_home_id:
                salary_persons.add(payslip.employee_id.address_home_id.id)
            row = fill_by_general(payslip)
            row2 = row.copy()
            row['T1RXXXXG14'] = get_column_14(payslip)

            sup_min_wage = payslip._get_line_total_by_code('SUPP_MIN_WAGE')

            values.append(row)
            if sup_min_wage:
                row['T1RXXXXG16'] = format_empty_cop(payslip._get_line_total_by_code('GROSS') - sup_min_wage)
                row['T1RXXXXG17'] = format_empty_cop(payslip._get_line_total_by_code('GROSS') - sup_min_wage)
                row['T1RXXXXG20'] = format_empty_cop(payslip._get_line_total_by_code('ESV_SMW_DIFF'))
                row2['T1RXXXXG9'] = '13'
                row2['T1RXXXXG12'] = ''
                row2['T1RXXXXG13'] = ''
                row2['T1RXXXXG14'] = ''
                row2['T1RXXXXG15'] = ''
                row2['T1RXXXXG16'] = ''
                row2['T1RXXXXG17'] = ''
                row2['T1RXXXXG18'] = format_empty_cop(sup_min_wage)
                row2['T1RXXXXG20'] = format_empty_cop(payslip._get_line_total_by_code('ESV_SMW'))
                values.append(row2)
        vacations = {}
        for payslip in HrPayslip.search([
            ('payment_type', '=', 'vacations'),
            ('date_from', '>=', date_from),
            ('date_from', '<=', date_to),
            ('company_id.id', '=', self.company_id.id),
            ('state', 'in', ('done', 'paid')),
        ]):
            if payslip.employee_id.id in vacations.keys():
                new_line = False
                row = vacations[payslip.employee_id.id][0]
                t1rxxxxg20 = vacations[payslip.employee_id.id][1]
                t1rxxxxg16 = vacations[payslip.employee_id.id][2]
            else:
                new_line = True
                row = fill_by_general(payslip)
                t1rxxxxg20 = 0
                t1rxxxxg16 = 0

            t1rxxxxg16 += payslip._get_line_total_by_code('VACATIONS_GROSS')
            t1rxxxxg20 += payslip._get_line_total_by_code('VACATIONS_ESV')

            row['T1RXXXXG16'] = format_empty_cop(t1rxxxxg16)
            row['T1RXXXXG17'] = format_empty_cop(t1rxxxxg16)
            row['T1RXXXXG20'] = format_empty_cop(t1rxxxxg20)

            if new_line:
                t1rxxxxg14 = ''
                if payslip.employee_id.address_home_id and payslip.employee_id.address_home_id.id not in salary_persons:
                    t1rxxxxg14 = get_column_14(payslip)
                row['T1RXXXXG8'] = '10'
                row['T1RXXXXG14'] = t1rxxxxg14
                values.append(row)

            vacations[payslip.employee_id.id] = (row, t1rxxxxg20, t1rxxxxg16)

        seak_lives = {}
        for payslip in HrPayslip.search([
            ('payment_type', '=', 'sick_leaves'),
            ('date_from', '>=', date_from),
            ('date_from', '<=', date_to),
            ('company_id.id', '=', self.company_id.id),
            ('state', 'in', ('done', 'paid')),
        ]):
            if 'MATERNITY_LEAVES_GROSS' not in payslip.line_ids.mapped('salary_rule_id.code'):
                if payslip.employee_id.id in seak_lives.keys():
                    new_line = False
                    row = seak_lives[payslip.employee_id.id][0]
                    t1rxxxxg20 = seak_lives[payslip.employee_id.id][1]
                    t1rxxxxg16 = seak_lives[payslip.employee_id.id][2]
                else:
                    new_line = True
                    row = fill_by_general(payslip)
                    t1rxxxxg20 = 0
                    t1rxxxxg16 = 0

                t1rxxxxg20 += payslip._get_line_total_by_code('SICK_LEAVES_EMP_ESV') + payslip._get_line_total_by_code('SICK_LEAVES_CIF_ESV')
                t1rxxxxg16 += payslip._get_line_total_by_code('SICK_LEAVES_EMP_GROSS') + payslip._get_line_total_by_code('SICK_LEAVES_CIF_GROSS')

                row['T1RXXXXG16'] = format_empty_cop(t1rxxxxg16)
                row['T1RXXXXG17'] = format_empty_cop(t1rxxxxg16)
                row['T1RXXXXG20'] = format_empty_cop(t1rxxxxg20)

                if new_line:
                    t1rxxxxg14 = ''
                    if payslip.employee_id.address_home_id and payslip.employee_id.address_home_id.id not in salary_persons:
                        t1rxxxxg14 = get_column_14(payslip)

                    t1rxxxxg12 = format_empty_cop(payslip.get_worked_time(date_from, date_to, ('ТН',)).get('days'))

                    row['T1RXXXXG8'] = '36' if payslip.employee_id.has_actual_disability_group(payslip.date_from) else '29'
                    row['T1RXXXXG14'] = t1rxxxxg14
                    row['T1RXXXXG12'] = t1rxxxxg12
                    values.append(row)

                seak_lives[payslip.employee_id.id] = (row, t1rxxxxg20, t1rxxxxg16)

        # Maternity part
        for payslip in HrPayslip.search([
            ('payment_type', '=', 'sick_leaves'),
            ('date_from', '>=', date_from),
            ('date_from', '<=', date_to),
            ('company_id.id', '=', self.company_id.id),
            ('state', 'in', ('done', 'paid')),
            ('line_ids.salary_rule_id.code', '=', 'MATERNITY_LEAVES_GROSS'),
        ]):
            days_total = (payslip.date_to - payslip.date_from).days + 1
            gross_total = payslip._get_line_total_by_code('MATERNITY_LEAVES_GROSS')
            gross_done = 0.0
            esv_total = payslip._get_line_total_by_code('MATERNITY_LEAVES_ESV')
            esv_done = 0.0

            mater_from, mater_to = mater_period(payslip, (date_from, date_to))

            while payslip.date_to > mater_from:
                mater_days = (mater_to - mater_from).days + 1

                mater_coef = mater_days / days_total

                next_month_from = (mater_from + relativedelta(months=1)).replace(day=1)
                next_month_to = (next_month_from + relativedelta(day=31))
                next_mater_from, next_mater_to = mater_period(payslip, (next_month_from, next_month_to))
                last_month = next_mater_from >= payslip.date_to

                if last_month:
                    t1rxxxxg16 = gross_total - gross_done
                    t1rxxxxg20 = esv_total - esv_done
                else:
                    t1rxxxxg16 = gross_total * mater_coef
                    gross_done += t1rxxxxg16
                    t1rxxxxg20 = esv_total * mater_coef
                    esv_done += t1rxxxxg20

                row = fill_by_general(payslip)

                row['T1RXXXXG8'] = '42'
                row['T1RXXXXG16'] = format_empty_cop(t1rxxxxg16)
                row['T1RXXXXG17'] = format_empty_cop(t1rxxxxg16)
                row['T1RXXXXG20'] = format_empty_cop(t1rxxxxg20)
                row['T1RXXXXG14'] = ''
                row['T1RXXXXG12'] = ''
                row['T1RXXXXG15'] = format_empty_int(mater_days)
                row['T1RXXXXG101'] = format_empty_int(mater_from.month)
                row['T1RXXXXG102'] = format_empty_int(mater_from.year)
                values.append(row)
                mater_to = next_mater_to
                mater_from = next_mater_from

        return values

    def _generate_data_addon4_table(self, date_from, date_to):

        def get_person_social_code(person_id, date_from, date_to):
            self.env.cr.execute('''
                SELECT  employee.id
                FROM    hr_payslip payslip,
                        hr_payslip_line pline,
                        hr_employee employee,
                        hr_salary_rule srule
                WHERE   payslip.employee_id = employee.id
                        AND payslip.id = pline.slip_id
                        AND pline.salary_rule_id = srule.id
                        AND srule.code = 'TAX_SOCIAL_BENEFIT'
                        AND payslip.state IN ('done', 'paid')  
                        AND payslip.company_id = %(company_id)s
                        AND payslip.date >= %(date_from)s
                        AND payslip.date <= %(date_to)s
                        AND employee.address_home_id = %(person_id)s    
            ''', {
                'person_id': person_id,
                'company_id': self.company_id.id,
                'date_from': date_from,
                'date_to': date_to,
            })
            raw_data = self.env.cr.fetchall()
            HrEmployee = self.env['hr.employee']
            for line in raw_data:
                employee = HrEmployee.browse(line[0])
                for benefit in employee.tax_social_benefit_ids:
                    if benefit.date_from <= date_from < benefit.date_to:
                        return benefit.tax_social_benefit_code_id.code
            return False

        values = []
        self.env.flush_all()
        self.env.cr.execute('''
            SELECT employee.name emp
              FROM hr_payslip payslip,
                   hr_payslip_line pline,
                   hr_employee employee,
                   hr_salary_rule srule,
                   hr_employee_income_feature_code codes
             WHERE payslip.employee_id = employee.id
               AND codes.id = srule.income_feature_code_id
               AND payslip.id = pline.slip_id
               AND pline.salary_rule_id = srule.id
               AND srule.income_feature_code_id is not null
               AND srule.report_kind is not null
               AND payslip.state IN ('done', 'paid')  
               AND payslip.company_id = %(company_id)s
               AND payslip.date_from >= %(date_from)s
               AND payslip.date_from <= %(date_to)s
               AND employee.address_home_id is null
             limit 1
        ''', {
            'company_id': self.company_id.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        err_data = self.env.cr.fetchall()
        if len(err_data) > 0:
            name = err_data[0][0]
            raise UserError(_("All employee should have filled person field. Check employee: %s") % name)

        self.env.cr.execute('''
            SELECT employee.address_home_id person, 
                   codes.code code,
                   srule.report_kind kind,
                   sum(pline.amount) amount
              FROM hr_payslip payslip,
                   hr_payslip_line pline,
                   hr_employee employee,
                   hr_salary_rule srule,
                   hr_employee_income_feature_code codes
             WHERE payslip.employee_id = employee.id
               AND codes.id = srule.income_feature_code_id
               AND payslip.id = pline.slip_id
               AND pline.salary_rule_id = srule.id
               AND srule.income_feature_code_id is not null
               AND srule.report_kind is not null
               AND payslip.state IN ('done', 'paid')  
               AND payslip.company_id = %(company_id)s
               AND payslip.date_from >= %(date_from)s
               AND payslip.date_from <= %(date_to)s
               AND codes.code not in ('169', '140')
             GROUP BY 1,2,3
             ORDER BY 1,2,3    
        ''', {
            'company_id': self.company_id.id,
            'date_from': date_from,
            'date_to': date_to,
        })

        raw_data = self.env.cr.fetchall()
        lines_data = {}
        for raw_line in raw_data:
            if not raw_line[0]:
                raise UserError(_("All employee should have filled person field"))
            key = (raw_line[0], raw_line[1])
            if lines_data.get(key):
                if lines_data[key].get(raw_line[2]):
                    lines_data[key][raw_line[2]] += raw_line[3]
                else:
                    lines_data[key][raw_line[2]] = raw_line[3]
            else:
                lines_data[key] = {raw_line[2]: raw_line[3]}

        ResPartner = self.env['res.partner']
        HrPayslipLine = self.env['hr.payslip.line']
        for key, data in lines_data.items():
            partner_id = ResPartner.browse(key[0])
            hire_orders = self.env['hr.order'].search([
                ('date_of_employment', '>=', date_from),
                ('date_of_employment', '<=', date_to),
                ('employee_id.address_home_id', '=', partner_id.id),
            ])
            hire_date = '';
            if hire_orders:
                hire_date = hire_orders[0].date_of_employment.strftime('%d.%m.%Y')
            social_code = get_person_social_code(partner_id.id, date_from, date_to)
            values.append({
                'T1RXXXXG02':   partner_id.vat or '',
                'T1RXXXXG03A':  data.get('income') or 0.0,
                'T1RXXXXG03':   data.get('income') or 0.0,
                'T1RXXXXG04A':  abs(data.get('pdfo') or 0.0),
                'T1RXXXXG04':   abs(data.get('pdfo') or 0.0),
                'T1RXXXXG5A':   abs(data.get('mt') or 0.0),
                'T1RXXXXG5':    abs(data.get('mt') or 0.0),
                'T1RXXXXG05':   key[1],
                # TODO: should implement multi hiring in one period
                'T1RXXXXG06D':  hire_date,
                'T1RXXXXG07D':  '',
                # TODO: should be implemented at next iteration
                'T1RXXXXG08':   social_code if social_code else '-',
                'T1RXXXXG09':   0,
            })

            for alimony_line in HrPayslipLine.search([
                ('slip_id.employee_id.address_home_id', '=', partner_id.id),
                ('slip_id.date_from', '>=', date_from),
                ('slip_id.date_from', '<=', date_to),
                ('slip_id.state', 'in', ['done', 'paid']),
                ('salary_rule_id.code', '=', 'ALIMONY'),
                ('benefit_line_id.receiver_id', '!=', False),
            ]):
                alimony_partner_id = alimony_line.benefit_line_id.receiver_id
                values.append({
                    'T1RXXXXG02': alimony_partner_id.vat or '',
                    'T1RXXXXG03A': abs(alimony_line.total) or 0.0,
                    'T1RXXXXG03': abs(alimony_line.total) or 0.0,
                    'T1RXXXXG05': '140',
                })

            for charity_line in HrPayslipLine.search([
                ('slip_id.employee_id.address_home_id', '=', partner_id.id),
                ('slip_id.date_from', '>=', date_from),
                ('slip_id.date_from', '<=', date_to),
                ('slip_id.state', 'in', ['done', 'paid']),
                ('salary_rule_id.code', '=', 'CHARITY'),
            ]):
                charity_pdfo = charity_line.slip_id._get_line_total_by_code('CHARITY_PDFO')
                charity_mt = charity_line.slip_id._get_line_total_by_code('CHARITY_MT')

                values.append({
                    'T1RXXXXG02': partner_id.vat or '',
                    'T1RXXXXG03A': abs(charity_line.total) or 0.0,
                    'T1RXXXXG03': abs(charity_line.total) or 0.0,
                    'T1RXXXXG04A': abs(charity_pdfo or 0.0),
                    'T1RXXXXG04': abs(charity_pdfo or 0.0),
                    'T1RXXXXG5A': abs(charity_mt or 0.0),
                    'T1RXXXXG5': abs(charity_mt or 0.0),

                    'T1RXXXXG05': '169',
                })

        for vendor_bill in self.env['account.move'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id.id', '=', self.company_id.id),
            ('partner_id.parent_id', '=', False),
            ('partner_id.is_company', '=', False),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
        ]):
            values.append({
                'T1RXXXXG02': vendor_bill.partner_id.vat or '',
                'T1RXXXXG03A': vendor_bill.amount_total or 0.0,
                'T1RXXXXG03': vendor_bill.amount_total or 0.0,
                'T1RXXXXG04A': '',
                'T1RXXXXG04': '',
                'T1RXXXXG5A': '',
                'T1RXXXXG5':  '',
                'T1RXXXXG05': 157,
                'T1RXXXXG06D': '',
                'T1RXXXXG07D': '',
                'T1RXXXXG08': '-',
                'T1RXXXXG09': 0,
            })

        return values

    def _generate_data_addon4(self, date_from, date_to):
        from_1 = date_from
        to_1 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month)[1])
        from_2 = date_from.replace(day=1, month=date_from.month + 1)
        to_2 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 1)[1], month=date_from.month + 1)
        from_3 = date_from.replace(day=1, month=date_from.month + 2)
        to_3 = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month + 2)[1], month=date_from.month + 2)

        values = {

            'J0510409M1_T1RXXXX': self._generate_data_addon4_table(from_1, to_1),
            'J0510409M2_T1RXXXX': self._generate_data_addon4_table(from_2, to_2),
            'J0510409M3_T1RXXXX': self._generate_data_addon4_table(from_3, to_3),
            'J0510409M1_HNM': 1,
            'J0510409M2_HNM': 2,
            'J0510409M3_HNM': 3,
        }

        return values

    def _recompute_values(self, values):
        super()._recompute_values(values)
        # ----------- addon 1 ------------
        for i in range(1, 4):
            addon = f'J0510109M{i}_'

            values[addon + 'R01G16'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG16')
            values[addon + 'R01G17'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG17')
            values[addon + 'R01G18'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG18')
            values[addon + 'R01G19'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG19')
            values[addon + 'R01G20'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG20')

        # ------------ addon 4 ------------
        for i in range(1, 4):
            addon = f'J0510409M{i}_'

            values[addon + 'R01G03A'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG03A')
            values[addon + 'R01G03'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG03')
            values[addon + 'R01G04A'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG04A')
            values[addon + 'R01G04'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG04')
            values[addon + 'R01G5A'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG5A')
            values[addon + 'R01G5'] = sum_amount_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG5')
            values[addon + 'R02G01I'] = len(values[addon + 'T1RXXXX'])
            values[addon + 'R02G02I'] = count_unique_format_empty_cop(values[addon + 'T1RXXXX'], 'T1RXXXXG5')

            values[addon + 'R00G01I'] = format_empty_int(count_unique_condition(
                values[addon + 'T1RXXXX'],
                'T1RXXXXG02',
                lambda row: str(row.get('T1RXXXXG05', '')) == '101'
            ))

            values[addon + 'R00G02I'] = format_empty_int(count_unique_condition(
                values[addon + 'T1RXXXX'],
                'T1RXXXXG02',
                lambda row: str(row.get('T1RXXXXG05', '')) == '102'
            ))

        # --------------main part ----------

        values['R01015G3'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M1_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '128',
        ))

        values['R01015G4'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M2_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '128',
        ))

        values['R01015G5'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M3_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '128',
        ))

        values['R01011G3'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M1_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) != '102' and str(row.get('T1RXXXXG05', '')) != '157',
        ) - to_float(values.get('R01013G3', 0)) - to_float(values.get('R01014G3', 0)) - to_float(values.get('R01015G3', 0)))

        values['R01011G4'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M2_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) != '102' and str(row.get('T1RXXXXG05', '')) != '157',
        ) - to_float(values.get('R01013G4', 0)) - to_float(values.get('R01014G4', 0)) - to_float(values.get('R01015G4', 0)))

        values['R01011G5'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M3_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) != '102' and str(row.get('T1RXXXXG05', '')) != '157',
        ) - to_float(values.get('R01013G5', 0)) - to_float(values.get('R01014G5', 0)) - to_float(values.get('R01015G5', 0)))

        values['R01012G3'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M1_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '102',
        ))

        values['R01012G4'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M2_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '102',
        ))

        values['R01012G5'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510409M3_T1RXXXX'],
            'T1RXXXXG03A',
            lambda row: str(row.get('T1RXXXXG05', '')) == '102',
        ))

        values['R01031G5'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG16',
            lambda row: str(row.get('T1RXXXXG8', '')) == '1',
        ) - to_float(values.get('R01035G5', 0)))

        values['R01021G3'] = sum_amount_format_empty_cop(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG17',
        )

        values['R01021G4'] = sum_amount_format_empty_cop(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG17',
        )

        values['R01021G5'] = sum_amount_format_empty_cop(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG17',
        )

        values['R01022G3'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R01022G4'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R01022G5'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R01025G3'] = sum_amount_format_empty_cop(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG18',
        )

        values['R01025G4'] = sum_amount_format_empty_cop(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG18',
        )

        values['R01025G5'] = sum_amount_format_empty_cop(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG18',
        )

        values['R01035G3'] = format_empty_cop(sum_amount_float(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG18',
        ) * 0.22)

        values['R01035G4'] = format_empty_cop(sum_amount_float(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG18',
        ) * 0.22)

        values['R01035G5'] = format_empty_cop(sum_amount_float(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG18',
        ) * 0.22)

        values['R01032G3'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG20',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R01032G4'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG20',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R01032G5'] = sum_amount_by_condition_format_empty_cop(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG20',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        )

        values['R010321G3'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        ) * 0.22)

        values['R010321G4'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        ) * 0.22)

        values['R010321G5'] = format_empty_cop(sum_amount_float_by_condition(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG17',
            lambda row: str(row.get('T1RXXXXG8', '')) == '2',
        ) * 0.22)

        values['R01031G3'] = format_empty_cop(sum_amount_float(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG20',
        ) - to_float(values.get('R01035G3', 0)))

        values['R01031G4'] = format_empty_cop(sum_amount_float(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG20',
        ) - to_float(values.get('R01035G4', 0)))

        values['R01031G5'] = format_empty_cop(sum_amount_float(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG20',
        ) - to_float(values.get('R01035G5', 0)))

        values['R0102G3'] = format_empty_cop(
            to_float(values.get('R01021G3', 0)) +
            to_float(values.get('R01022G3', 0)) +
            to_float(values.get('R01023G3', 0)) +
            to_float(values.get('R01024G3', 0)) +
            to_float(values.get('R01025G3', 0))
        )

        values['R0102G4'] = format_empty_cop(
            to_float(values.get('R01021G4', 0)) +
            to_float(values.get('R01022G4', 0)) +
            to_float(values.get('R01023G4', 0)) +
            to_float(values.get('R01024G4', 0)) +
            to_float(values.get('R01025G4', 0))
        )

        values['R0102G5'] = format_empty_cop(
            to_float(values.get('R01021G5', 0)) +
            to_float(values.get('R01022G5', 0)) +
            to_float(values.get('R01023G5', 0)) +
            to_float(values.get('R01024G5', 0)) +
            to_float(values.get('R01025G5', 0))
        )

        values['R0103G3'] = format_empty_cop(
            to_float(values.get('R01031G3', 0)) +
            to_float(values.get('R01032G3', 0)) +
            to_float(values.get('R01033G3', 0)) +
            to_float(values.get('R01034G3', 0)) +
            to_float(values.get('R01035G3', 0)) +
            to_float(values.get('R01036G3', 0))
        )

        values['R0103G4'] = format_empty_cop(
            to_float(values.get('R01031G4', 0)) +
            to_float(values.get('R01032G4', 0)) +
            to_float(values.get('R01033G4', 0)) +
            to_float(values.get('R01034G4', 0)) +
            to_float(values.get('R01035G4', 0)) +
            to_float(values.get('R01036G4', 0))
        )

        values['R0103G5'] = format_empty_cop(
            to_float(values.get('R01031G5', 0)) +
            to_float(values.get('R01032G5', 0)) +
            to_float(values.get('R01033G5', 0)) +
            to_float(values.get('R01034G5', 0)) +
            to_float(values.get('R01035G5', 0)) +
            to_float(values.get('R01036G5', 0))
        )

        values['R0107G3'] = format_empty_cop(
            to_float(values.get('R0103G3', 0)) +
            to_float(values.get('R0104G3', 0)) -
            to_float(values.get('R0106G3', 0))
        )

        values['R0107G4'] = format_empty_cop(
            to_float(values.get('R0103G4', 0)) +
            to_float(values.get('R0104G4', 0)) -
            to_float(values.get('R0106G4', 0))
        )

        values['R0107G5'] = format_empty_cop(
            to_float(values.get('R0103G5', 0)) +
            to_float(values.get('R0104G5', 0)) -
            to_float(values.get('R0106G5', 0))
        )

        values['R0108G3'] = format_empty_cop(
            to_float(values.get('R0107G3', 0)) +
            to_float(values.get('R0107G4', 0)) +
            to_float(values.get('R0107G5', 0))
        )

        values['R108G3'] = format_empty_int(count_unique_condition(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ж'
        ))

        values['R108G4'] = format_empty_int(count_unique_condition(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ж'
        ))

        values['R108G5'] = format_empty_int(count_unique_condition(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ж'
        ))

        values['R109G3'] = format_empty_int(count_unique_condition(
            values['J0510109M1_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ч'
        ))

        values['R109G4'] = format_empty_int(count_unique_condition(
            values['J0510109M2_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ч'
        ))

        values['R109G5'] = format_empty_int(count_unique_condition(
            values['J0510109M3_T1RXXXX'],
            'T1RXXXXG7S',
            lambda row: row.get('T1RXXXXG6', '') == 'Ч'
        ))

        values['R105G3'] = format_empty_int(
            to_float(values.get('R108G3', 0)) +
            to_float(values.get('R109G3', 0))
        )

        values['R105G4'] = format_empty_int(
            to_float(values.get('R108G4', 0)) +
            to_float(values.get('R109G4', 0))
        )

        values['R105G5'] = format_empty_int(
            to_float(values.get('R108G5', 0)) +
            to_float(values.get('R109G5', 0))
        )

        values['R0101G3'] = format_empty_cop(
            to_float(values.get('R01011G3', 0)) +
            to_float(values.get('R01012G3', 0)) +
            to_float(values.get('R01013G3', 0)) +
            to_float(values.get('R01014G3', 0)) +
            to_float(values.get('R01015G3', 0))
        )

        values['R0101G4'] = format_empty_cop(
            to_float(values.get('R01011G4', 0)) +
            to_float(values.get('R01012G4', 0)) +
            to_float(values.get('R01013G4', 0)) +
            to_float(values.get('R01014G4', 0)) +
            to_float(values.get('R01015G4', 0))
        )

        values['R0101G5'] = format_empty_cop(
            to_float(values.get('R01011G5', 0)) +
            to_float(values.get('R01012G5', 0)) +
            to_float(values.get('R01013G5', 0)) +
            to_float(values.get('R01014G5', 0)) +
            to_float(values.get('R01015G5', 0))
        )

    # -------------------------------------------------------------------------
    # GENERATE (EXPORT) XML
    # -------------------------------------------------------------------------

    @api.model
    def _get_part_xml_template(self, part_name):
        part_name = self._get_doc_name(part_name)
        return f'selferp_l10n_ua_salary.hr_salary_esv_pdfo_report_template_export_xml_{part_name}'

    @api.model
    def _get_period_type(self):
        return '2'

    # -------------------------------------------------------------------------
    # OTHER
    # -------------------------------------------------------------------------

    def _check_included_in_values(self):
        parts = self._get_part_names()

        self.invalidate_recordset(['values'])
        for record in self:
            values = record.values or {}
            changed = False

            # compute count
            appendixes = defaultdict(lambda: 0)
            for part_name in parts[1:]:
                doc_name = self._get_doc_name(part_name)
                field_name = f'include_{part_name}'
                if self._fields.get(field_name) and self[field_name]:
                    appendixes[doc_name] += 1
                else:
                    appendixes[doc_name] += 0

            # check changes
            for doc_name, count in appendixes.items():
                index = doc_name[5]
                count = count or ''

                field_name_count = f'R06{index}G3'
                if values[field_name_count] != count:
                    values[field_name_count] = count
                    changed = True

                field_name_page_count = f'R06{index}G4'
                if values[field_name_page_count] != count:
                    values[field_name_page_count] = count
                    changed = True

            # write changes
            if changed:
                record.with_context(
                    skip_vat_tax_report_check_included_docs=True,
                    skip_vat_tax_report_recompute_values=True,
                ).write({
                    'values': values,
                })
