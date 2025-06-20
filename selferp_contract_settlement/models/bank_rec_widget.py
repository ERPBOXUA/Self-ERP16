from odoo import models, fields, api


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        domain="[('partner_id', '=', partner_id)]",
        related='st_line_id.contract_id',
        depends=['st_line_id'],
    )

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        # Since 'bank.rec.widget' model is not "standard" and doesn't allow to save value
        # of 'contract_id' via 'related' field, this hack is used to save changes of
        # 'contract_id' directly into 'st_line_id'
        contract_id = self.contract_id

        if self.st_line_id.contract_id != contract_id:
            self.st_line_id.write({
                'contract_id': contract_id and contract_id.id or None,
            })
