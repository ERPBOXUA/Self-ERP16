from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrPayrollContractBenefit(models.Model):
    _name = 'hr.payroll.contract.benefit'
    _inherit = 'hr.benefit.mixin'
    _description = "Payroll Contract Benefit"

    contract_id = fields.Many2one(
        comodel_name='hr.contract',
        string="Contract",
        required=True,
    )

    date_from = fields.Date(
        string="From Date",
        required=True,
        default=fields.Date.today,
    )

    date_to = fields.Date(
        string="To Date",
    )

    payroll_benefit_id = fields.Many2one(
        comodel_name='hr.payroll.benefit',
        string="Accruals / Deductions",
        required=True,
    )

    receiver_id = fields.Many2one(
        comodel_name='res.partner',
        string="Receiver Partner",
    )

    display_receiver = fields.Char(
        string="Receiver",
        compute='_compute_display_receiver'
    )

    children_ids = fields.One2many(
        comodel_name='hr.payroll.contract.benefit.alimony.children',
        inverse_name='hr_payroll_contract_benefit_id',
        string="Children",
    )

    benefit_name = fields.Char(
        related='payroll_benefit_id.name',
    )

    benefit_type = fields.Selection(
        related='payroll_benefit_id.type',
    )

    is_alimony = fields.Boolean(
        related='payroll_benefit_id.is_alimony',
    )

    charge_type = fields.Selection(
        related='payroll_benefit_id.charge_type',
    )

    display_details = fields.Char(
        related='payroll_benefit_id.display_details',
    )

    benefit_code = fields.Char(
        related='payroll_benefit_id.code',
    )

    schedule_pay = fields.Selection(
        related='payroll_benefit_id.schedule_pay',
    )

    @api.depends('payroll_benefit_id', 'receiver_id')
    @api.onchange('payroll_benefit_id', 'receiver_id')
    def _compute_display_receiver(self):
        for rec in self:
            rec.display_receiver = (
                rec.payroll_benefit_id
                and rec.payroll_benefit_id.type == 'deduction'
                and rec.payroll_benefit_id.is_alimony
                and rec.receiver_id
                and rec.receiver_id.name
                or ''
            )

    @api.onchange('payroll_benefit_id')
    def _update_accounts(self):
        for rec in self:
            if rec.payroll_benefit_id:
                if rec.payroll_benefit_id.account_debit_id:
                    rec.account_debit_id = rec.payroll_benefit_id.account_debit_id
                if rec.payroll_benefit_id.account_credit_id:
                    rec.account_credit_id = rec.payroll_benefit_id.account_credit_id

    @api.constrains('children_ids')
    def _check_children(self):
        for benefit in self.filtered(lambda rec: rec.benefit_type == 'deduction' and rec.is_alimony):
            if not benefit.children_ids or benefit.children_ids.filtered(lambda rec: not (rec.children_age and rec.children_number)):
                raise ValidationError(_("Alimony records must contain information about the children and their ages"))

    def name_get(self):
        result = []
        for rec in self:
            display_name = rec.payroll_benefit_id.name
            if rec.date_from and rec.date_to:
                display_name += ' (%s - %s)' % (rec.date_from, rec.date_to)
            elif rec.date_from:
                display_name += ' (%s)' % rec.date_from
            result.append((rec.id, display_name))
        return result
