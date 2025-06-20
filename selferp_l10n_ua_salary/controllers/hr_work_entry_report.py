import json

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError


class HrWorkEntryPrintController(http.Controller):

    @http.route('/hr_work_entry_print', auth='user', type='http', sitemap=False)
    def hr_work_entry_print_pdf(self, **kwargs):
        values = dict(**kwargs)

        work_entries_domain = [
            ('employee_id', 'in', json.loads(values['employee_ids'])),
            ('date_start', '>=', values['date_from']),
            ('date_stop', '<=', values['date_to']),
            ('state', 'in', ('validated', 'draft')),
        ]

        work_entries = request.env['hr.work.entry'].search(work_entries_domain)

        if not work_entries:
            raise UserError(_("There are no work entries for given employees and date range"))

        company = request.env['res.company'].browse(int(values['company']))
        department = request.env['hr.department'].browse(int(values['department'])) if int(values['department']) else None
        values.update({
            'company_name': company.name,
            'company_registry': company.company_registry,
            'department_name': department.name if department else '',
            'date_from': fields.Date.from_string(values['date_from']).strftime('%d.%m.%Y'),
            'date_to': fields.Date.from_string(values['date_to']).strftime('%d.%m.%Y'),
        })

        employees = {}

        for work_entry in work_entries:
            if work_entry.employee_id.id in employees:
                emp = employees.get(work_entry.employee_id.id)
            else:
                if work_entry.employee_id.job_id:
                    emp_name = work_entry.employee_id.display_name + ', ' + work_entry.employee_id.job_id.display_name
                else:
                    emp_name = work_entry.employee_id.display_name

                emp = {
                    'id': work_entry.employee_id.id,
                    'registration_number': work_entry.employee_id.registration_number or '',
                    'gender': work_entry.employee_id.gender or '',
                    'name': emp_name,
                    'days': {},
                }

                if work_entry.employee_id.contract_id.wage_type == 'hourly':
                    emp['contract_wage'] = work_entry.employee_id.contract_id.hourly_wage or 0
                else:
                    emp['contract_wage'] = work_entry.employee_id.contract_id.wage or 0

            # if work_entry.work_entry_type_id.timesheet_ccode in ('Р', 'НУ', 'РН', 'ВЧ', 'РВ', 'ТН'):
            if work_entry.work_entry_type_id.timesheet_ccode:
                days = emp.get('days')
                day = days.get(work_entry.date_start.day)

                if day:
                    day['duration'] = int(day.get('duration') + work_entry.duration)
                    days[work_entry.date_start.day] = day
                    emp['hours_count'] = int(emp.get('hours_count') + work_entry.duration)
                else:
                    days.update({
                        work_entry.date_start.day: {
                            'day': work_entry.date_start.day,
                            'day_type': work_entry.work_entry_type_id.timesheet_ccode,
                            'duration': int(work_entry.duration),
                        },
                    })

                    emp.update({
                        'days_count': emp.get('days_count', 0) + 1,
                        'hours_count': emp.get('hours_count', 0) + int(work_entry.duration),
                    })

            if work_entry.work_entry_type_id.timesheet_ccode == 'НУ':
                emp['hours_nu'] = int(emp.get('hours_nu', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ccode == 'РН':
                emp['hours_rn'] = int(emp.get('hours_rn', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ccode == 'ВЧ':
                emp['hours_vch'] = int(emp.get('hours_vch', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ccode == 'РВ':
                emp['hours_rv'] = int(emp.get('hours_rv', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ccode == 'ТН':
                emp['hours_tn'] = int(emp.get('hours_tn', 0) + work_entry.duration)
                emp['code_26_27_hours'] = int(emp.get('code_26_27_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode in (8, 9, 10):
                emp['code_8_10_hours'] = int(emp.get('code_8_10_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode in (11, 15, 17, 22):
                emp['code_11_22_hours'] = int(emp.get('code_11_22_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 18:
                emp['code_18_hours'] = int(emp.get('code_28_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 19:
                emp['code_19_hours'] = int(emp.get('code_19_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 20:
                emp['code_20_hours'] = int(emp.get('code_20_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 21:
                emp['code_21_hours'] = int(emp.get('code_21_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 23:
                emp['code_23_hours'] = int(emp.get('code_23_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 24:
                emp['code_24_hours'] = int(emp.get('code_24_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode == 25:
                emp['code_25_hours'] = int(emp.get('code_25_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode in (26, 27):
                emp['code_26_27_hours'] = int(emp.get('code_26_27_hours', 0) + work_entry.duration)
            elif work_entry.work_entry_type_id.timesheet_ncode in (28, 29, 30):
                emp['code_28_30_hours'] = int(emp.get('code_28_30_hours', 0) + work_entry.duration)

            employees[work_entry.employee_id.id] = emp

        values['employees'] = employees.values()

        for emp in employees.values():
            for property_name in (
                    'days_count',
                    'hours_count',
                    'hours_nu',
                    'hours_rn',
                    'hours_vch',
                    'hours_rv',
                    'hours_tn',
                    'code_8_10_hours',
                    'code_11_22_hours',
                    'code_18_hours',
                    'code_19_hours',
                    'code_20_hours',
                    'code_21_hours',
                    'code_23_hours',
                    'code_24_hours',
                    'code_25_hours',
                    'code_26_27_hours',
                    'code_28_30_hours',
                    'contract_wage',
            ):
                property_name_all = property_name + '_all'
                values[property_name_all] = values.get(property_name_all, 0) + emp.get(property_name, 0)

        body = request.env['ir.ui.view']._render_template(
            'selferp_l10n_ua_salary.hr_work_entry_report_template',
            values=values,
        )

        bodies, html_ids, header, footer, specific_paperformat_args = request.env['ir.actions.report']._prepare_html(body, report_model=False)

        file_content = request.env['ir.actions.report']._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=True,
            specific_paperformat_args={
                'data-report-margin-top': 5,
                'data-report-header-spacing': 1,
                'data-report-margin-bottom': 5,
                'data-report-footer-spacing': 1,
            },
        )

        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(file_content)),
            ('Content-Disposition', http.content_disposition('work_entry_report_' + fields.Date.to_string(fields.Date.today()) + '.pdf')),
        ]
        return request.make_response(file_content, headers=pdf_http_headers)
