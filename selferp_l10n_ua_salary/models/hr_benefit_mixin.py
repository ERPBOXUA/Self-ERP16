from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_repr, float_round


PERCENT_DIGITS = (16, 3)


class HrBenefitMixin(models.AbstractModel):
    _name = 'hr.benefit.mixin'
    _description = "Salary Benefit Mixin"

    amount_base = fields.Selection(
        selection=[
            ('fixed', "Fixed Amount"),
            ('percent', "Percents"),
            ('percent_in_wages', "Percents In Wages"),
        ],
        string="Amount Base",
        required=True,
        default='fixed',
    )

    base_rule_code = fields.Char(
        string="Amount Base Rule Code",
        help="""
By default, the value of the rule coded NET_TECHNICAL for deductions and the rule coded BASIC for accruals are used as input values for percent computation.
If you need to use the value of another rule, enter its code here.
        """,
    )

    display_base_rule_code = fields.Char(
        string="Amount Base Rule",
        compute='_compute_display_base_rule_code',
    )

    fixed_amount = fields.Float(
        string="Fixed Amount",
        digits='Payroll',
    )

    percent = fields.Float(
        string="Percents",
        digits=PERCENT_DIGITS,
    )

    percent_in_wages = fields.Float(
        string="Percents In Wages",
        digits=PERCENT_DIGITS,
    )

    display_amount = fields.Char(
        string="Amount",
        compute='_compute_display_amount',
    )

    account_in_next_period = fields.Boolean(
        string="Take Into Account In Next Period",
        default=False,
    )

    account_debit_id = fields.Many2one(
        comodel_name='account.account',
        string="Debit Account",
        company_dependent=True,
        domain=[('deprecated', '=', False)],
    )

    account_credit_id = fields.Many2one(
        comodel_name='account.account',
        string="Credit Account",
        company_dependent=True,
        domain=[('deprecated', '=', False)],
    )

    @api.constrains('amount_base', 'fixed_amount', 'percent', 'percent_in_wages')
    def _constraint_amount(self):
        currency = self.env.company.currency_id
        decimal_places = currency.decimal_places
        for rec in self:
            if rec.amount_base == 'fixed' and float_is_zero(rec.fixed_amount, precision_digits=decimal_places):
                raise ValidationError(_("Fixed amount must be set for the accruals or deductions record '%s'") % rec.display_name)
            elif rec.amount_base == 'percent' and float_is_zero(rec.percent, precision_digits=PERCENT_DIGITS[1]):
                raise ValidationError(_("Percent value must be set for the accruals or deductions record '%s'") % rec.display_name)
            elif rec.amount_base == 'percent_in_wages' and float_is_zero(rec.percent_in_wages, precision_digits=PERCENT_DIGITS[1]):
                raise ValidationError(_("Percent in wages must be set for the accruals or deductions record '%s'") % rec.display_name)

    @api.depends('amount_base', 'fixed_amount', 'percent', 'percent_in_wages')
    @api.onchange('amount_base', 'fixed_amount', 'percent', 'percent_in_wages')
    def _compute_display_amount(self):
        currency = self.env.company.currency_id
        decimal_places = currency.decimal_places
        for rec in self:
            if rec.amount_base == 'fixed':
                rec.display_amount = float_repr(float_round(rec.fixed_amount, decimal_places), decimal_places) + currency.symbol
            elif rec.amount_base == 'percent':
                rec.display_amount = '%.1f %%' % (rec.percent * 100,)
            elif rec.amount_base == 'percent_in_wages':
                rec.display_amount = _("%.1f %% in wage incl.") % (rec.percent_in_wages * 100,)
            else:
                rec.display_amount = ''

    @api.depends('amount_base', 'base_rule_code')
    @api.onchange('amount_base', 'base_rule_code')
    def _compute_display_base_rule_code(self):
        for rec in self:
            rec.display_base_rule_code = rec.amount_base in ('percent', 'percent_in_wages') and rec.base_rule_code or ''

    def _compute_amount(self, wage):
        self.ensure_one()
        result = 0.0
        wage = wage or 0.0
        if self.amount_base == 'fixed':
            result = self.fixed_amount
        elif self.amount_base == 'percent' and not float_is_zero(self.percent, precision_digits=PERCENT_DIGITS[1]):
            result = wage * self.percent
        elif self.amount_base == 'percent_in_wages' and not float_is_zero(self.percent_in_wages, precision_digits=PERCENT_DIGITS[1]):
            result = wage * self.percent_in_wages / (1 + self.percent_in_wages)
        return result
