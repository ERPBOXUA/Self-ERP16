import logging

from odoo import fields, models


_logger = logging.getLogger(__name__)


class StockInventoryMember(models.Model):
    _name = 'stock.inventory.member'
    _description = "Stock Inventory Member"

    inventory_id = fields.Many2one(
        comodel_name='stock.inventory',
        ondelete='cascade',
        required=True,
        readonly=True,
        index=True,
        string="Stock Inventory",
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        required=True,
        string="Employee",
    )
    job_id = fields.Many2one(
        related='employee_id.job_id',
    )
    role = fields.Selection(
        selection=[
            ('chair', "Commission Chair"),
            ('member', "Commission Member"),
        ],
        required=True,
    )
