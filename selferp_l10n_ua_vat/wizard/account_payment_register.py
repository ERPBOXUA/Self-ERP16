from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _init_payments(self, to_process, edit_mode=False):
        payments = super()._init_payments(to_process, edit_mode=edit_mode)

        for payment, vals in zip(payments, to_process):
            linked_sale_order = vals['batch']['lines'].mapped('linked_sale_order_id')
            if linked_sale_order:
                payment.line_ids.filtered(lambda r: r.account_type == 'asset_receivable').write({
                    'linked_sale_order_id': linked_sale_order[0].id,
                })

            linked_purchase_order = vals['batch']['lines'].mapped('linked_purchase_order_id')
            if linked_purchase_order:
                payment.line_ids.filtered(lambda r: r.account_type == 'liability_payable').write({
                    'linked_purchase_order_id': linked_purchase_order[0].id,
                })

        return payments
