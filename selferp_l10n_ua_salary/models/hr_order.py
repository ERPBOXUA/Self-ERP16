from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrOrder(models.Model):
    _name = 'hr.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Order block"

    name = fields.Char(
        string="Order Name",
    )

    type_id = fields.Many2one(
        comodel_name='hr.order.type',
        required=True,
        string="Order Type"
    )

    is_recruitment_fields_visible = fields.Boolean(
        compute='_compute_type_selected',
    )

    is_dismissal_fields_visible = fields.Boolean(
        compute='_compute_type_selected',
    )

    is_granting_leave_fields_visible = fields.Boolean(
        compute='_compute_type_selected',
    )

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        required=True,
        string="Employee",
    )

    order_date = fields.Date(
        required=True,
        string="Order date",
    )

    notes = fields.Html(
        string="Notes",
    )

    contract_id = fields.Many2one(
        comodel_name='hr.contract',
        string="Contract",
    )

    date_of_employment = fields.Date(
        string="Date of employment",
    )

    date_of_dismissal = fields.Date(
        string="Date of dismissal",
    )

    article_of_the_labor_code = fields.Char(
        string="Article of the Labor Code",
    )

    basis = fields.Char(
        string="Basis",
    )

    vacation_date_from = fields.Date(
        string="Vacation date from",
    )

    vacation_date_to = fields.Date(
        string="Vacation date to",
    )

    work_date_from = fields.Date(
        string="Work date from",
    )

    work_date_to = fields.Date(
        string="Work date to",
    )

    type_of_vacation = fields.Char(
        string="Type of vacation",
    )

    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.contract_id = False
            rec.date_of_employment = False
            rec.date_of_dismissal = False
            rec.vacation_date_from = False
            rec.vacation_date_to = False
            rec.work_date_from = False
            rec.work_date_to = False

    @api.onchange('contract_id')
    def _onchange_contract(self):
        for rec in self:
            if self.contract_id.date_start:
                rec.date_of_employment = self.contract_id.date_start
            if self.contract_id.date_end:
                rec.date_of_dismissal = self.contract_id.date_end

    @api.onchange('type_id')
    def _compute_type_selected(self):
        recruitment = self.env.ref('selferp_l10n_ua_salary.hr_order_type_recruitment')
        dismissal = self.env.ref('selferp_l10n_ua_salary.hr_order_type_dismissal')
        granting_leave = self.env.ref('selferp_l10n_ua_salary.hr_order_type_granting_leave')

        for rec in self:
            rec.is_recruitment_fields_visible = rec.type_id == recruitment
            rec.is_dismissal_fields_visible = rec.type_id == dismissal
            rec.is_granting_leave_fields_visible = rec.type_id == granting_leave

    @api.constrains('name')
    def _check_name(self):
        for rec in self:
            if rec.name and self.search_count([('name', '=', rec.name), ('id', '!=', rec.id)]):
                raise UserError(_("Order block is already exist with this Order Name"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals['name'] or vals['name'] == '':
                order_type = self.env['hr.order.type'].browse(vals['type_id'])
                if order_type:
                    vals['name'] = order_type.type_group_id.property_sequence_id._next()
        return super().create(vals_list)
