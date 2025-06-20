from odoo import api, models, fields, _


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    is_salary_payment = fields.Boolean(
        string="Salary Payment",
        default=False,
        copy=False,
    )
    payslip_id = fields.Many2one(
        comodel_name='hr.payslip',
        ondelete='restrict',
        domain="[('state', '=', 'done'), ('employee_id.address_home_id', '=', partner_id)]",
        string="Payslip",
        copy=False,
    )

    @api.onchange('is_salary_payment')
    def _onchange_is_salary_payment(self):
        for record in self:
            if not record.is_salary_payment:
                record.payslip_id = None

    def action_show(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Bank Statement Lines"),
            'res_model': self._name,
            'domain': [
                ('id', 'in', self.ids),
            ],
            'view_mode': 'tree,kanban,form',
        }
