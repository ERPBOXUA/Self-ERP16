from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        domain="[('partner_id', '=', partner_id), ('operation_type', '=', default_contract_operation_type)]",
    )
    
    default_contract_operation_type = fields.Char(
        compute='_compute_default_contract_operation_type',
    )

    @api.depends('move_type', 'line_ids.amount_residual', 'contract_id')
    def _compute_payments_widget_to_reconcile_info(self):
        super()._compute_payments_widget_to_reconcile_info()

        for rec in self:
            vals = rec.invoice_outstanding_credits_debits_widget
            if rec.contract_id and vals and vals.get('content'):
                new_content = []
                rec.invoice_has_outstanding = False

                for line in vals['content']:
                    move = self.browse(line['move_id'])
                    if move.line_ids.filtered(lambda l: l.contract_id == rec.contract_id and l._is_contract_open_balance()):
                        new_content.append(line)

                if new_content:
                    rec.invoice_outstanding_credits_debits_widget['content'] = new_content
                    rec.invoice_has_outstanding = True
                else:
                    rec.invoice_outstanding_credits_debits_widget = False

    @api.depends('move_type')
    @api.onchange('move_type')
    def _compute_default_contract_operation_type(self):
        for rec in self:
            rec.default_contract_operation_type = 'purchase' if rec.move_type in ['in_invoice', 'in_refund', 'in_receipt'] else 'sale'

    def _find_contract_from_values(self, values):
        if 'contract_id' not in values:
            if 'reversed_entry_id' in values:
                parent_contract = self.browse(values['reversed_entry_id']).contract_id
                if parent_contract and parent_contract.id:
                    values['contract_id'] = parent_contract.id
        return values

    def new(self, values=None, origin=None, ref=None):
        values = self._find_contract_from_values(values)
        return super().new(values, origin, ref)

    @api.model_create_multi
    def create(self, values):
        values = self._find_contract_from_values(values)
        return super().create(values)

    def write(self, values):
        values = self._find_contract_from_values(values)
        return super().write(values)
