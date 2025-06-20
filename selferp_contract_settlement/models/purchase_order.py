from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    contract_id = fields.Many2one(
        comodel_name='account.contract',
        string="Contract",
        domain="[('partner_id', '=', partner_id), ('operation_type', '=', 'purchase')]",
    )

    def action_create_invoice(self):
        res = super().action_create_invoice()

        invoices = None
        if 'res_id' in res:
            invoices = self.env['account.move'].browse(res['res_id'])
        else:
            if 'domain' in res:
                ids = res['domain'][0][2]
                invoices = self.env['account.move'].browse(ids)

        if invoices:
            for invoice in invoices:
                for line in invoice.line_ids:
                    if line.account_id and line.account_id.account_type == 'liability_payable':
                        line.contract_id = self.contract_id

        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if vals and self.contract_id:
            vals['contract_id'] = self.contract_id.id
        return vals
