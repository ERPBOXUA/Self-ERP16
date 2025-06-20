from odoo import models, fields


class HrPayslipCreatePaymentLine(models.TransientModel):
    _name = 'hr.payslip.create_payment.line'
    _description = "Payslip Create Payment Wizard Line"

    wizard_id = fields.Many2one(
        comodel_name='hr.payslip.create_payment',
        ondelete='cascade',
        required=True,
    )

    date = fields.Date(
        string="Date",
        required=True,
    )

    payslip_id = fields.Many2one(
        comodel_name='hr.payslip',
        ondelete='cascade',
        required=True,
        readonly=True,
    )
    payslip_partner_id = fields.Many2one(
        related='payslip_id.employee_id.address_home_id',
        string="Partner",
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='payslip_id.currency_id',
    )

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        ondelete='restrict',
        domain="[('type', 'in', ('bank', 'cash'))]",
        string="Journal",
    )
    bank_statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        ondelete='restrict',
        domain="[('journal_id', '=', journal_id)]",
        string="Bank Statement",
    )
