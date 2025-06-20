import itertools

from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        domain="[('account_type', '=', 'expense')]",
        ondelete='restrict',
    )

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        ondelete='restrict',
    )

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Analytic Account",
        ondelete='restrict',
    )

    non_fixed_working_hours = fields.Boolean(
        string="Non-fixed working hours",
    )

    payroll_contract_benefit_ids = fields.One2many(
        comodel_name='hr.payroll.contract.benefit',
        inverse_name='contract_id',
    )

    timesheet_based_salary = fields.Boolean(
        string="Timesheet-based Salary",
        default=False,
    )

    @api.constrains('payroll_contract_benefit_ids')
    def _check_date_range(self):
        ContractBenefit = self.env['hr.payroll.contract.benefit']
        benefit_types = defaultdict(lambda: ContractBenefit)
        for contract in self:
            for benefit in contract.payroll_contract_benefit_ids:
                benefit_types[(benefit.payroll_benefit_id.id or None, benefit.charge_type or None, benefit.receiver_id.id or None)] |= benefit
            for key, benefits in benefit_types.items():
                if len(benefits) > 1:
                    for benefit1, benefit2 in itertools.combinations(benefits, 2):
                        benefit_from1 = benefit1.date_from
                        benefit_to1 = benefit1.date_to or contract.date_end or fields.Date.today()
                        benefit_from2 = benefit2.date_from
                        benefit_to2 = benefit2.date_to or contract.date_end or fields.Date.today()
                        if (
                            benefit_from1 <= benefit_from2 <= benefit_to1
                            or benefit_from1 <= benefit_to2 <= benefit_to1
                            or benefit_from2 <= benefit_from1 <= benefit_to2
                            or benefit_from2 <= benefit_to1 <= benefit_to2
                        ):
                            raise ValidationError(_("Periods for benefits of the same type should not overlap"))
