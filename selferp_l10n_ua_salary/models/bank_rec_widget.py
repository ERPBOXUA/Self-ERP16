from odoo import models, fields, api


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    is_salary_payment = fields.Boolean(
        related='st_line_id.is_salary_payment',
        depends=['st_line_id'],
        readonly=False,
    )
    payslip_id = fields.Many2one(
        related='st_line_id.payslip_id',
        depends=['st_line_id'],
        readonly=False,
    )

    @api.onchange('is_salary_payment', 'payslip_id')
    def _onchange_salary_payment(self):
        # Since 'bank.rec.widget' model is not "standard" and doesn't allow to save value
        # of 'payslip_id' via 'related' field, this hack is used to save changes of
        # 'payslip_id' directly into 'st_line_id'
        if not self.is_salary_payment:
            self.payslip_id = None
        self.st_line_id.write({
            'is_salary_payment': self.is_salary_payment,
            'payslip_id': self.is_salary_payment and self.payslip_id and self.payslip_id.id or None,
        })
