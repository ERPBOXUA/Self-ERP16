from odoo import models, fields, api


class HrPayslipBenefitLine(models.Model):
    _name = 'hr.payslip.benefit.line'
    _inherit = ['hr.benefit.type.mixin', 'hr.benefit.mixin']
    _description = "Payslip Benefit Line"

    payslip_id = fields.Many2one(
        comodel_name='hr.payslip',
        string="Payslip",
        required=True,
        ondelete='cascade',
    )

    mode = fields.Selection(
        selection=[
            ('manual', "Manual"),
            ('auto', "Automatic"),
        ],
        string="Mode",
        default='manual',
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
        comodel_name='hr.payslip.benefit.line.alimony.children',
        inverse_name='hr_payslip_benefit_line_id',
        string="Children",
    )

    @api.depends('receiver_id')
    @api.onchange('receiver_id')
    def _compute_display_receiver(self):
        for rec in self:
            rec.display_receiver = (
                rec.type == 'deduction'
                and rec.is_alimony
                and rec.receiver_id
                and rec.receiver_id.name
                or ''
            )
