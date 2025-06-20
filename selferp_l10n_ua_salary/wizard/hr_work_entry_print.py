import json
import urllib

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError


class HrWorkEntryPrint(models.TransientModel):
    _name = 'hr.work.entry.print'
    _description = "Timesheet Print Wizard"

    date_from = fields.Date(
        string="From",
        required=True,
    )

    date_to = fields.Date(
        string="To",
        required=True,
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        string="Department",
        company_dependent=True,
    )

    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string="Employees",
    )

    mode = fields.Selection(
        selection=[
            ('random', "Random Employee"),
            ('by_department', "By Department"),
        ],
        string="Selection Mode",
        default='random',
    )

    @api.model
    def _employees_with_contracts(self, employees, date_from, date_to):
        if employees:
            contracts = employees._get_contracts(date_from, date_to, states=('open', 'close'))
            return contracts.mapped('employee_id')
        return employees

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res = res or {}
        if not ('date_from' in res or 'date_to' in res):
            today = fields.Date.today()
            date_from = date(today.year, today.month, 1)
            date_to = date_from + relativedelta(months=1) - relativedelta(days=1)
            res.update({
                'date_from': date_from,
                'date_to': date_to,
            })
        active_employee_ids = self.env.context.get('active_employee_ids')
        if active_employee_ids:
            employee = self._employees_with_contracts(
                self.env['hr.employee'].browse(active_employee_ids).exists(),
                res['date_from'],
                res['date_to'],
            )
            if employee:
                res['employee_ids'] = [Command.set(employee.ids)]
        return res

    @api.onchange('mode')
    def _onchange_mode(self):
        Employee = self.env['hr.employee']
        if self.mode == 'by_department':
            employees = self.department_id and Employee.search([('department_id', '=', self.department_id.id)]) or None
        else:
            active_employee_ids = self.env.context.get('active_employee_ids')
            employees = active_employee_ids and Employee.browse(active_employee_ids).exists() or None
        self.employee_ids = self._employees_with_contracts(employees, self.date_from, self.date_to)

    @api.onchange('department_id')
    def _onchange_department_id(self):
        employees = self.department_id and self.env['hr.employee'].search([('department_id', '=', self.department_id.id)]) or None
        self.employee_ids = self._employees_with_contracts(employees, self.date_from, self.date_to)

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.mode == 'random' and not self.employee_ids:
            active_employee_ids = self.env.context.get('active_employee_ids')
            employees = active_employee_ids and self.env['hr.employee'].browse(active_employee_ids).exists() or None
            self.employee_ids = self._employees_with_contracts(employees, self.date_from, self.date_to)

    def action_print_timesheet(self):
        self.ensure_one()

        if not (self.date_from and self.date_to):
            raise UserError(_("Please set the date range which will be used to select employees you want to print timesheet for"))
        if not self.employee_ids:
            raise UserError(_("Please select the department or the employees you want to print timesheet for"))

        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('date_start', '>=', self.date_from),
            ('date_stop', '<=', self.date_to),
            ('state', 'in', ('validated', 'draft')),
        ])
        if not work_entries:
            raise UserError(_("There are no work entries for given employees and date range"))

        values = {
            'company': self.env.company.id,
            'department': self.department_id.id if self.department_id else 0,
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
            'employee_ids': str(self.employee_ids.ids).replace(' ', '')
        }

        url_params = urllib.parse.urlencode(values)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url':  '/hr_work_entry_print?%s' % url_params,
        }
