from collections import defaultdict

from odoo import api, models, fields, Command, _
from odoo.exceptions import UserError


class HrPayslipCreatePayment(models.TransientModel):
    _name = 'hr.payslip.create_payment'
    _description = "Payslip Create Payment Wizard"

    default_date = fields.Date(
        string="Default Date",
        default=lambda self: fields.Date.today(),
    )

    default_journal_id = fields.Many2one(
        comodel_name='account.journal',
        ondelete='restrict',
        domain="[('type', 'in', ('bank', 'cash'))]",
        string="Default Journal",
    )
    default_bank_statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        ondelete='restrict',
        domain="[('journal_id', '=', default_journal_id)]",
        string="Default Bank Statement",
    )

    line_ids = fields.One2many(
        comodel_name='hr.payslip.create_payment.line',
        inverse_name='wizard_id',
        string="Lines",
    )
    line_count = fields.Integer(
        compute='_compute_lines',
    )
    line_first_id = fields.Many2one(
        comodel_name='hr.payslip.create_payment.line',
        compute='_compute_lines',
    )

    line_first_date = fields.Date(
        related='line_first_id.date',
        depends=['line_first_id'],
        readonly=False,
    )
    line_first_payslip_id = fields.Many2one(
        related='line_first_id.payslip_id',
        depends=['line_first_id'],
    )
    line_first_partner_id = fields.Many2one(
        related='line_first_id.payslip_partner_id',
        depends=['line_first_id'],
    )
    line_first_currency_id = fields.Many2one(
        related='line_first_id.currency_id',
        depends=['line_first_id'],
    )
    line_first_amount = fields.Monetary(
        related='line_first_id.amount',
        depends=['line_first_id'],
        currency_field='line_first_currency_id',
    )
    line_first_journal_id = fields.Many2one(
        related='line_first_id.journal_id',
        depends=['line_first_id'],
        readonly=False,
    )
    line_first_bank_statement_id = fields.Many2one(
        related='line_first_id.bank_statement_id',
        depends=['line_first_id'],
        domain="[('journal_id', '=', line_first_journal_id)]",
        readonly=False,
    )

    @api.depends('line_ids')
    def _compute_lines(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.line_first_id = record.line_ids and record.line_ids[0] or None

    @api.onchange('default_date')
    def _onchange_default_date(self):
        for record in self:
            if record.default_date:
                record.line_ids.write({
                    'date': record.default_date,
                })

    @api.onchange('default_journal_id')
    def _onchange_default_journal_id(self):
        for record in self:
            if record.default_journal_id:
                if record.default_bank_statement_id and record.default_bank_statement_id.journal_id != record.default_journal_id:
                    record.default_bank_statement_id = None

                for line in record.line_ids:
                    update_values = {}

                    if line.journal_id != record.default_journal_id:
                        update_values['journal_id'] = record.default_journal_id.id

                        if line.bank_statement_id and line.bank_statement_id.journal_id != record.default_journal_id:
                            update_values['bank_statement_id'] = record.default_bank_statement_id and record.default_bank_statement_id or None

                    if update_values:
                        line.write(update_values)

    @api.onchange('default_bank_statement_id')
    def _onchange_default_bank_statement_id(self):
        for record in self:
            if record.default_bank_statement_id:
                record.line_ids.write({
                    'bank_statement_id': record.default_bank_statement_id.id,
                })

    def action_confirm(self):
        self.ensure_one()

        # check lines
        if self.line_ids.filtered(lambda r: not r.journal_id):
            raise UserError(_("Each bank statement line must have a journal reference"))

        # create bank statement lines
        payments = self.env['account.bank.statement.line'].create([
            {
                'statement_id': line.bank_statement_id and line.bank_statement_id.id or None,
                'journal_id': line.journal_id.id,
                'is_salary_payment': True,
                'payslip_id': line.payslip_id.id,
                'partner_id': line.payslip_id.employee_id.address_home_id.id,
                'amount': -line.amount,
                'date': line.date,
                'payment_ref': _("Salary payment %s", line.payslip_id.number),
            }
            for line in self.line_ids
        ])

        # remove wizard
        self.unlink()

        # show bank statement lines
        return payments.action_show()

    @api.model
    def create_and_show(self, payslips):
        if not payslips:
            return

        today = fields.Date.today()

        lines = []
        for payslip in payslips:
            # check partner
            if not payslip.employee_id.address_home_id:
                raise UserError(_("No associated contact/partner has been established for employee %s", payslip.employee_id.name))

            # collect all NET
            amounts = defaultdict(lambda: 0)
            for payslip_line in payslip.line_ids:
                if payslip_line.code == 'NET' or payslip_line.code.endswith('_NET'):
                    amounts[payslip_line.code] += payslip_line.total

            # create line per each NET
            for code, amount in amounts.items():
                lines.append(Command.create({
                    'date': today,
                    'payslip_id': payslip.id,
                    'amount': amount,
                }))

        # create wizard
        wizard = self.create({
            'default_date': today,
            'line_ids': lines,
        })

        # show wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _("Create Payments") if len(lines) > 1 else _("Create Payment"),
            'res_model': wizard._name,
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
