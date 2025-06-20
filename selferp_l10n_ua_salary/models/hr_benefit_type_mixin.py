from odoo import models, fields, api, _


class HrBenefitTypeMixin(models.AbstractModel):
    _name = 'hr.benefit.type.mixin'
    _description = "Benefit Type Salary Mixin"

    name = fields.Char(
        string="Name",
    )

    type = fields.Selection(
        selection=[
            ('accrual', "Accrual"),
            ('deduction', "Deduction"),
        ],
        string="Type",
        default='accrual',
    )

    code = fields.Char(
        string="Code",
    )

    is_alimony = fields.Boolean(
        string="Is Alimony",
        default=False,
    )

    charge_type = fields.Selection(
        selection=[
            ('charity', "General Charity"),
            ('bonus', "Bonus"),
        ],
        string="Charge Type",
    )

    display_details = fields.Char(
        string="Details",
        compute='_compute_display_details',
    )

    schedule_pay = fields.Selection(
        selection=[
            ('monthly', "Monthly"),
            ('quarterly', "Quarterly"),
            ('semi-annually', "Semi-annually"),
            ('annually', "Annually"),
        ],
        string="Scheduled Pay",
        default='monthly',
    )

    @api.depends('type', 'is_alimony', 'charge_type')
    @api.onchange('type', 'is_alimony', 'charge_type')
    def _compute_display_details(self):
        charge_type = dict(self._fields['charge_type']._description_selection(self.env))
        for rec in self:
            if rec.type == 'deduction':
                rec.display_details = rec.is_alimony and _("Alimony") or ''
            else:
                rec.display_details = rec.charge_type and charge_type.get(rec.charge_type) or ''
