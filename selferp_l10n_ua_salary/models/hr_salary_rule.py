from odoo import models, fields, api


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    struct_id = fields.Many2one(
        ondelete='cascade',
    )

    use_employee_expense_account = fields.Boolean(
        string="Use Employee Contract's Expense Account",
        default=False,
    )

    income_feature_code_id = fields.Many2one(
        comodel_name='hr.employee.income_feature_code',
        string="Income Feature Codes",
        ondelete='restrict',
    )

    report_kind = fields.Selection(
        selection=[
            ('income', "Income"),
            ('esv', "ESV"),
            ('pdfo', "PDFO"),
            ('mt', "Military tax"),
        ],
        string="Report kind",
    )

    account_debit_code = fields.Char(
        string="Debit Account Code",
        compute='_compute_debit_account_code',
        inverse='_inverse_account_debit',
        readonly=False,
    )

    account_credit_code = fields.Char(
        string="Credit Account Code",
        compute='_compute_credit_account_code',
        inverse='_inverse_account_credit',
        readonly=False,
    )

    @api.depends('account_debit')
    @api.onchange('account_debit')
    def _compute_debit_account_code(self):
        for rec in self:
            rec.account_debit_code = rec.account_debit and rec.account_debit.code or None

    @api.depends('account_credit')
    @api.onchange('account_credit')
    def _compute_credit_account_code(self):
        for rec in self:
            rec.account_credit_code = rec.account_credit and rec.account_credit.code or None

    def _update_account(self, code_name, account_name):
        companies = self.env.context.get('force_rules_companies') or self.env['res.company'].sudo().search([])
        if companies and hasattr(self, code_name) and hasattr(self, account_name):
            Account = self.env['account.account'].sudo()
            for rec in self:
                account_code = getattr(rec, code_name) or None
                for company in companies:
                    account = Account.search([('code', '=', account_code), ('company_id', '=', company.id)], limit=1)
                    setattr(rec.with_company(company), account_name, account or None)

    def _inverse_account_debit(self):
        self._update_account('account_debit_code', 'account_debit')

    def _inverse_account_credit(self):
        self._update_account('account_credit_code', 'account_credit')

    def _compute_rule(self, localdict):
        localdict['current_rule'] = self
        payslip = localdict.get('payslip')
        payslip = payslip and payslip.dict or None
        if payslip:
            rule_eval_context = payslip.env.context.get('rule_eval_context')
            if rule_eval_context:
                rule_eval_context['localdict'] = localdict
        result = super()._compute_rule(localdict)
        if payslip:
            result = payslip._post_process_compute_rule(self, localdict, result)
        localdict.pop('current_rule', True)
        return result

    def _emulate_compute_rule(self, localdict):
        return super()._compute_rule(localdict)
