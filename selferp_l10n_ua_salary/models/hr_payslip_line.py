from odoo import models, fields, api


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'
    _order = 'contract_id, sequence, id'

    account_debit_id = fields.Many2one(
        string="Debit Account",
        comodel_name='account.account',
        compute='_compute_accounting_data',
    )

    account_credit_id = fields.Many2one(
        string="Credit Account",
        comodel_name='account.account',
        compute='_compute_accounting_data',
    )

    benefit_line_id = fields.Many2one(
        comodel_name='hr.payslip.benefit.line',
        string="Benefit",
    )

    project_id = fields.Many2one(
        comodel_name='project.project',
        string="Project",
    )

    account_date_from = fields.Date(
        string="Account Date From",
    )

    account_date_to = fields.Date(
        string="Account Date To",
    )

    @api.depends('salary_rule_id', 'salary_rule_id.account_debit', 'salary_rule_id.account_credit')
    @api.onchange('salary_rule_id')
    def _compute_accounting_data(self):
        for rec in self:
            if rec.salary_rule_id.use_employee_expense_account:
                contract = rec.slip_id and rec.slip_id._get_employee_actual_contract() or None
                rec.account_debit_id = contract and contract.account_id or rec.salary_rule_id.account_debit
            elif rec.benefit_line_id and rec.benefit_line_id.account_debit_id:
                rec.account_debit_id = rec.benefit_line_id.account_debit_id
            else:
                rec.account_debit_id = rec.salary_rule_id.account_debit
            if rec.benefit_line_id and rec.benefit_line_id.account_credit_id:
                rec.account_credit_id = rec.benefit_line_id.account_credit_id
            else:
                rec.account_credit_id = rec.salary_rule_id.account_credit
