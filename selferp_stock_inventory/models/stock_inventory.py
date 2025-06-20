import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import groupby


_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _name = 'stock.inventory'
    _inherit = 'address_custom.mixin'
    _description = "Stock Inventory"

    name = fields.Char(
        default=lambda self: _("New"),
        states={'done': [('readonly', True)]},
        copy=False,
        readonly=True,
        string="Reference",
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('done', "Done"),
        ],
        default='draft',
        copy=False,
        string="Status",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        index=True,
        required=True,
        readonly=True,
        string="Company",
    )
    inventory_date = fields.Date(
        default=fields.Datetime.now,
        states={'done': [('readonly', True)]},
        required=True,
        string="Inventory Date",
        help="Choose a date to get the inventory at that date",
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        states={'done': [('readonly', True)]},
        string="User",
    )
    location_ids = fields.Many2many(
        comodel_name='stock.location',
        compute='_compute_location_ids',
        context={'active_test': False},
        string="Locations",
    )
    inventory_line_ids = fields.One2many(
        comodel_name='stock.inventory.line',
        inverse_name='inventory_id',
        states={'done': [('readonly', True)]},
        string="Stock Inventory Lines",
    )
    inventory_member_ids = fields.One2many(
        comodel_name='stock.inventory.member',
        inverse_name='inventory_id',
        states={'done': [('readonly', True)]},
        string="Stock Inventory Members",
    )
    note = fields.Char(
        string="Note",
    )
    stock_move_line_count = fields.Integer(
        compute='_compute_stock_move_line_count',
        string="Stock Move Count",
    )

    @api.depends('inventory_line_ids.location_id')
    def _compute_location_ids(self):
        for record in self:
            record.location_ids = record.inventory_line_ids.mapped('location_id')

    @api.depends('inventory_line_ids')
    def _compute_stock_move_line_count(self):
        for rec in self:
            rec.stock_move_line_count = len(rec.inventory_line_ids)

    def action_confirm(self):
        for rec in self:
            rec.name = rec.company_id.sequence_stock_inventory_id.next_by_id() or _("New")

        self._apply_inventory()

        self.write({'state': 'done'})

    def action_show_stock_move_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Move Lines"),
            'res_model': 'stock.move.line',
            'domain': [
                ('stock_inventory_line_id', 'in', self.inventory_line_ids.ids),
            ],
            'view_mode': 'tree,form',
        }

    def _apply_inventory(self):
        """ Apply inventory line by line.
            Based on stock.quant._apply_inventory() method.

        :return:
        """
        self.ensure_one()

        if not self.user_has_groups('stock.group_stock_manager'):
            raise UserError(_("Only a stock manager can validate an inventory adjustment."))

        StockMove = self.env['stock.move'].with_context(inventory_mode=False)
        today = fields.Date.today()

        # group lines by accounting date
        for accounting_date, lines in groupby(self.inventory_line_ids, key=lambda line: line.accounting_date):
            if not accounting_date:
                accounting_date = today

            # prepare stock move values
            move_vals = []

            for line in lines:
                # get values by quant
                quant = line.stock_quant_id

                if float_compare(line.inventory_diff_quantity, 0, precision_rounding=line.product_uom_id.rounding) > 0:
                    values = quant._get_inventory_move_values(
                        line.inventory_diff_quantity,
                        line.product_id.with_company(quant.company_id).property_stock_inventory,
                        line.location_id,
                        out=False,
                    )
                else:
                    values = quant._get_inventory_move_values(
                        -line.inventory_diff_quantity,
                        line.location_id,
                        line.product_id.with_company(quant.company_id).property_stock_inventory,
                        out=True,
                    )

                # set reference on inventory line
                values['move_line_ids'][0][2]['stock_inventory_line_id'] = line.id

                # append values
                move_vals.append(values)

            # create and validate stock moves
            moves = StockMove.with_context(force_period_date=accounting_date).create(move_vals)
            moves._action_done()

        # set inventory date into locations
        locations = self.inventory_line_ids.mapped('stock_quant_id.location_id')
        locations.write({
            'last_inventory_date': self.inventory_date,
        })

        # update quant values
        date_by_location = {loc: loc._get_next_inventory_date() for loc in locations}
        for line in self.inventory_line_ids:
            quant = line.stock_quant_id
            quant.write({
                'inventory_date': date_by_location[quant.location_id],
                'inventory_quantity': 0,
                'user_id': False,
                'inventory_diff_quantity': 0,
                'inventory_quantity_set': False,
            })

        # update AVG cost for all lines
        self.inventory_line_ids._compute_avg_cost()
