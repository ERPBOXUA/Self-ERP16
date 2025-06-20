from odoo import models, fields, api


class HrSchedule(models.Model):
    _name = 'hr.schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Staff Schedule"
    _rec_name = 'number'

    number = fields.Char(
        string="Number",
    )

    schedule_date = fields.Date(
        string="Date",
        required=True,
        default=lambda self: fields.Date.today(),
    )

    document_date = fields.Date(
        string="Document date",
    )

    basis = fields.Char(
        string="Basis",
        required=True,
    )

    responsible_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        ondelete='restrict',
        string="Responsible Person",
    )

    line_ids = fields.One2many(
        comodel_name='hr.schedule.line',
        inverse_name='schedule_id',
        string="Schedule Lines",
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        ondelete='restrict',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Currency",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('number'):
                vals['number'] = self.env['ir.sequence'].next_by_code('hr.schedule.number.sequence')
        return super().create(vals_list)
