from odoo import models, fields, _
from odoo.exceptions import UserError

from odoo.addons.selferp_l10n_ua_vat.models.account_move import VAT_INVOICE_STAGES


class AccountMoveVATInvoiceChangeStageWizard(models.TransientModel):
    _name = 'account.move.vat_invoice.change_stage'
    _description = "Change Stage VAT Invoice"

    vat_invoice_stage = fields.Selection(
        selection=VAT_INVOICE_STAGES,
        string="Stage",
        required=True,
        default='prepared',
    )

    def action_confirm(self):
        moves = self.env['account.move'].browse(self._context.get('active_ids', []))

        if moves:
            if moves.filtered(lambda r: r.move_type not in ('vat_invoice', 'vat_adjustment_invoice')):
                raise UserError(_("Change stage available only for VAT Invoices and VAT Adjustment Invoices"))

            moves.write({'vat_invoice_stage': self.vat_invoice_stage})
