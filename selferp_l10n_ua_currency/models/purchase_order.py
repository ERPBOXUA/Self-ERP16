from odoo import api, models, fields, Command, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_import = fields.Boolean(
        string="Import",
        default=False,
        help="Check the box if the purchase order include import operations. The Exchange rate on the date of advance payments (prepayments) and/or Customs Declaration will be taken for calculating the cost of imported products",
    )

    landed_cost_ids = fields.Many2many(
        comodel_name='stock.landed.cost',
        compute='_compute_landed_cost',
    )
    landed_cost_count = fields.Integer(
        compute='_compute_landed_cost',
    )

    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency',
        default=lambda self: self.env.company.currency_id,
    )
    is_company_currency = fields.Boolean(
        compute='_compute_currency',
    )

    @api.onchange('company_id', 'currency_id')
    @api.depends('company_id', 'currency_id')
    def _compute_currency(self):
        for record in self:
            record.company_currency_id = record.company_id.currency_id
            record.is_company_currency = record.company_currency_id == record.currency_id

    def _compute_landed_cost(self):
        StockLandedCost = self.env['stock.landed.cost']
        for record in self:
            record.landed_cost_ids = StockLandedCost.search([('picking_ids', 'in', record.picking_ids.ids)])
            record.landed_cost_count = len(record.landed_cost_ids)

    @api.onchange('is_import', 'order_line')
    def _onchange_is_import(self):
        self._check_import_taxes()

    @api.onchange('currency_id')
    def _onchange_currency(self):
        self.is_import = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        self._check_import_taxes()

        return records

    def write(self, values):
        res = super().write(values)

        self._check_import_taxes()

        return res

    def _check_import_taxes(self):
        for record in self:
            if record.is_import and record.order_line:
                record.order_line.write({
                    'taxes_id': None,
                })

    def button_confirm(self):
        for record in self:
            if (
                record.is_import
                and record.order_line.filtered(lambda r: r.product_id and r.product_id.type in ('product', 'consu'))
                and record.order_line.filtered(lambda r: r.product_id and r.product_id.type not in ('product', 'consu'))
            ):
                raise UserError(_("You can't confirm an import order with different type of products! Create separate purchase orders for each product type, please."))

        # confirm as usual
        return super().button_confirm()

    def action_create_invoice(self):
        if len(self) == 1 and not self.is_import:
            return super().action_create_invoice()

        for purchase in self:
            # check not empty import order
            if (
                purchase.is_import
                and purchase.order_line.filtered(
                    lambda r: not r.display_type
                              and r.product_id
                              and r.product_id.type in ('product', 'consu')
                )
            ):
                # get linked stock pickings
                picking_to_invoice = purchase.picking_ids.filtered(lambda r: r.state == 'done' and not r.vendor_bill_id)

                if not picking_to_invoice:
                    raise UserError(_("There are no any stock picking to invoice"))

                # for each picking create a vendor bill
                for picking in picking_to_invoice:
                    picking._create_import_vendor_bill()

            else:
                # create as usual
                super(PurchaseOrder, purchase).action_create_invoice()

        # open all linked moves
        return self.action_view_invoice()

    def action_show_landed_costs(self):
        self.ensure_one()

        if self.landed_cost_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Landed Cost"),
                'res_model': 'stock.landed.cost',
                'res_id': self.landed_cost_ids[0].id,
                'view_mode': 'form',
            }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Landed Costs"),
                'res_model': 'stock.landed.cost',
                'domain': [
                    ('picking_ids', 'in', self.picking_ids.ids),
                ],
                'view_mode': 'tree,form',
            }

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()

        # set import mark
        invoice_vals['is_import_vendor_bill'] = self.is_import

        return invoice_vals
