from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_property_account_accountable_id(self):
        accounts_model = self.env['account.account']
        account_accountable = accounts_model.search([
            ('code', '=', '372100'),
            ('company_id', '=', self.env.company.id),
        ])
        if not account_accountable:
            account_accountable = accounts_model.search([
                ('code', '=', '372100'),
                ('company_id', '=', False),
            ])
        return account_accountable and account_accountable.id or None

    property_account_accountable_id = fields.Many2one(
        comodel_name='account.account',
        string="Account Accountable",
        company_dependent=True,
        default=lambda self: self._default_property_account_accountable_id(),
        domain="""[
            ('account_type', '=', 'liability_payable'), 
            ('deprecated', '=', False), 
            ('company_id', '=', current_company_id),
        ]""",
        help="This account will be used in relationships with partner as accountable person",
    )

    work_employee_ids = fields.One2many(
        comodel_name='hr.employee',
        inverse_name='work_contact_id',
        string="Work-related Employees",
        groups="hr.group_hr_user",
        help="Related employees based on their work address"
    )
