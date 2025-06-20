from odoo import models, fields


class HrPayrollContractBenefitAlimonyChildren(models.Model):
    _name = 'hr.payroll.contract.benefit.alimony.children'
    _description = "Children on whom alimony is paid"

    hr_payroll_contract_benefit_id = fields.Many2one(
        comodel_name='hr.payroll.contract.benefit',
        string="Contract Benefit",
        required=True,
        ondelete='cascade',
    )

    children_age = fields.Selection(
        selection=[
            ('under_6', "Under 6 y.o."),
            ('from_6_to_18', "From 6 to 18 y.o."),
            ('from_18_to_23', "From 18 to 23 y.o."),
        ],
        string="Age Of Children",
        required=True,
    )

    children_number = fields.Integer(
        string="Number Of Children",
        default=1,
        required=True,
    )
