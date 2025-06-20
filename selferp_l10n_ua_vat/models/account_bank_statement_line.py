from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    linked_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Sale Order",
        domain="[('partner_id', '=', partner_id)]",
    )

    linked_purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Linked Purchase Order",
        domain="[('partner_id', '=', partner_id)]",
    )

    refund = fields.Boolean(
        string="Refund",
    )

    def _contract_changed(self):
        super()._contract_changed()

        for record in self:
            if record.linked_sale_order_id and record.linked_sale_order_id.contract_id != record.contract_id:
                record.linked_sale_order_id = None
            if record.linked_purchase_order_id and record.linked_purchase_order_id.contract_id != record.contract_id:
                record.linked_purchase_order_id = None
