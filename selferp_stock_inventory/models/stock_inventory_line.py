import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class StockInventoryLine(models.Model):
    _name = 'stock.inventory.line'
    _description = "Stock Inventory Line"

    inventory_id = fields.Many2one(
        comodel_name='stock.inventory',
        ondelete='cascade',
        required=True,
        readonly=True,
        index=True,
        string="Stock Inventory",
    )
    stock_quant_id = fields.Many2one(
        comodel_name='stock.quant',
        readonly=True,
    )
    product_id = fields.Many2one(
        related='stock_quant_id.product_id',
    )
    product_uom_id = fields.Many2one(
        related='product_id.uom_id',
    )
    location_id = fields.Many2one(
        related='stock_quant_id.location_id',
    )
    owner_id = fields.Many2one(
        related='stock_quant_id.owner_id',
    )
    accounting_date = fields.Date(
        related='stock_quant_id.accounting_date',
    )
    company_currency_id = fields.Many2one(
        related='inventory_id.company_id.currency_id',
    )
    avg_cost = fields.Monetary(
        compute='_compute_avg_cost',
        currency_field='company_currency_id',
        store=True,
        string="Average Cost",
    )
    quantity = fields.Float(
        digits='Product Unit of Measure',
        readonly=True,
        string="Quantity",
        help="Quantity of product, in the default unit of measure of the product",
    )
    inventory_quantity = fields.Float(
        digits='Product Unit of Measure',
        string="Counted Quantity",
        help="The product's counted quantity.",
    )
    inventory_diff_quantity = fields.Float(
        compute='_compute_inventory_diff_quantity',
        digits='Product Unit of Measure',
        store=True,
        string="Difference",
        help="Indicates the gap between the product's theoretical quantity and its counted quantity.",
    )

    def _compute_avg_cost(self):
        for line in self:
            line.avg_cost = line.product_id.with_company(line.inventory_id.company_id).avg_cost

    @api.depends('inventory_quantity')
    def _compute_inventory_diff_quantity(self):
        for line in self:
            line.inventory_diff_quantity = line.inventory_quantity - line.quantity
