from odoo import models, fields


class StockPickingCustomsDeclarationLine(models.Model):
    _name = 'stock.picking.customs_declaration.line'
    _description = "Stock picking customs declaration line"

    stock_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        ondelete='cascade',
        required=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        ondelete='restrict',
        domain=[('landed_cost_ok', '=', True)],
        required=True,
        string="Landed Cost",
    )

    description = fields.Text(
        string="Description",
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field='company_currency_id',
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_company_currency_id',
        default=lambda self: self.env.company.currency_id,
    )

    def _compute_company_currency_id(self):
        for record in self:
            record.company_currency_id = self.env.company.currency_id
