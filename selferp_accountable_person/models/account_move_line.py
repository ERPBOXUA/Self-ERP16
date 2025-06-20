from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends(
        'display_type',
        'company_id',
        'partner_id',
        'partner_id.property_account_accountable_id',
        'move_id.is_advance_report',
    )
    def _compute_account_id(self):
        super()._compute_account_id()
        for rec in self:
            if (
                rec.account_id
                and rec.account_id.account_type == 'liability_payable'
                and rec.move_id.move_type == 'in_invoice'
                and rec.move_id.is_advance_report
                and rec.partner_id
                and rec.partner_id.property_account_accountable_id
            ):
                rec.account_id = rec.partner_id.property_account_accountable_id
