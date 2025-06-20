from odoo import models, fields, api, _


class HrPayrollBenefit(models.Model):
    _name = 'hr.payroll.benefit'
    _description = "Payroll Benefit"
    _inherit = 'hr.benefit.type.mixin'
    _order = 'id'

    name = fields.Char(
        required=True,
        translate=True,
        copy=False,
    )

    code = fields.Char(
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('hr.payroll.benefit.sequence.code'),
        copy=False,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
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

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', "Name must be unique"),
        ('code_uniq', 'UNIQUE (code)', "Code must be unique"),
    ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        if not default.get('code'):
            default['code'] = _("%s.copy") % (self.code or '')
        return super().copy(default)
