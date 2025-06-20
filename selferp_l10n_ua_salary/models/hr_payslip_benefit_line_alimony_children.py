from odoo import models, fields


class HrPayslipBenefitLineAlimonyChildren(models.Model):
    _name = 'hr.payslip.benefit.line.alimony.children'
    _description = "Children on whom alimony is paid"

    hr_payslip_benefit_line_id = fields.Many2one(
        comodel_name='hr.payslip.benefit.line',
        string="Payslip Benefit Line",
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
