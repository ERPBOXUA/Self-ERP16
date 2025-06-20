from odoo import api, fields, models, _


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        domain="[('partner_id', '=', partner_id)]",
        context="{'default_partner_id': partner_id}",
    )

    @api.depends('contract_id')
    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        self._contract_changed()

    def action_save_close(self):
        ret = super().action_save_close()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account_accountant.action_bank_statement_line_form_bank_rec_widget',
        )
        return [action, ret]

    def action_edit_record_from_kanban(self):
        return {
            'name': _("Edit transaction"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'res_id': self.id,
            'views': [[False, 'form']],
            'view_id': 'view_account_bank_statement_line_form_edit',
            'target': 'new',
        }

    def _contract_changed(self):
        # you may override if you need
        pass
