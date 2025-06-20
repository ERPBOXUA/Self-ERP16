from odoo import models, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if self._get_report(report_ref).report_name in (
            'selferp_l10n_ua_sale_print_form.account_move_template_act',
            'selferp_l10n_ua_sale_print_form.account_move_template_invoice',
        ):
            moves = self.env['account.move'].browse(res_ids)
            if any([
                moves.mapped('asset_id'),
                self.env['account.asset'].search_count(['|', ('move_asset_on_run_id', 'in', moves.ids), ('move_asset_sell_id', 'in', moves.ids)]),
            ]):
                raise UserError(_("Asset's moves could not be printed."))

        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
