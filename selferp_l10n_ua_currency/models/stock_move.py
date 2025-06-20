from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    company_currency_id = fields.Many2one(
        related='picking_id.company_currency_id',
    )

    customs_declaration_cost = fields.Monetary(
        string="Customs Declaration Cost",
        currency_field='company_currency_id',
        compute='_compute_customs_declaration_cost',
    )

    customs_cost = fields.Monetary(
        string="Customs Cost",
        currency_field='company_currency_id',
        default=0,
    )

    customs_duty_amount = fields.Monetary(
        string="Customs Duty Amount",
        currency_field='company_currency_id',
        default=0,
    )

    excise_duty_amount = fields.Monetary(
        string="Excise Duty",
        currency_field='company_currency_id',
        default=0,
    )

    vat_amount = fields.Monetary(
        string="VAT amount",
        currency_field='company_currency_id',
        default=0,
    )

    customs_fee = fields.Monetary(
        string="Customs Fee",
        currency_field='company_currency_id',
        default=0,
    )

    import_adjustment_to_move_id = fields.Many2one(
        comodel_name='stock.move',
        ondelete='cascade',
        copy=False,
    )

    @api.depends(
        'quantity_done',
        'purchase_line_id.price_unit',
        'picking_id.customs_declaration_currency_rate',
        'company_currency_id',
    )
    @api.onchange('quantity_done')
    def _compute_customs_declaration_cost(self):
        for record in self:
            qty = record.quantity_done
            price = record.purchase_line_id.price_unit
            rate = record.picking_id.customs_declaration_currency_rate
            if qty and price and rate:
                record.customs_declaration_cost = qty * price * rate
            else:
                record.customs_declaration_cost = 0

    def get_import_price_unit(self):
        company_currency = self.picking_id.company_currency_id
        currency_rate = self.get_import_currency_rate()
        return company_currency.round(self.purchase_line_id.price_unit * currency_rate)

    def get_svl_import_currency_rate(self):
        self.ensure_one()

        # The stock move is used here to provide reference to
        # stock picking and purchase order in one record,
        # and here is no matter which stock move used.
        currency_rate_value = self.get_import_currency_rate()

        # We have to round the currency rate to unit price,
        # because on create SVL record system use unit price
        # instead of currency rate (like in invoice/bill), and
        # so we will have difference in cents else.
        currency_unit_price = self.purchase_line_id.price_unit or 1.0
        company_currency_unit_price = self.company_currency_id.round(currency_unit_price * currency_rate_value)
        currency_rate_value = company_currency_unit_price / currency_unit_price

        # return corrected currency rate
        return currency_rate_value

    def get_import_currency_rate(self):
        self.ensure_one()

        picking = self.picking_id
        if not (picking and picking.is_import):
            raise UserError(_("Currency rate compute allowed to import purchase orders only."))

        # check advances
        advances = picking.advance_line_ids.sorted('date')
        if advances:
            company_currency = picking.company_currency_id
            purchase_line = self.purchase_line_id
            purchase = purchase_line.order_id

            amount_advance = sum(picking.advance_line_ids.mapped('abs_amount_residual_currency'))

            # if advanced fully
            if (
                company_currency.compare_amounts(amount_advance, purchase.amount_untaxed) >= 0
                and (len(advances) == 1 or len(set(advances.mapped('currency_rate_back'))) == 1)
            ):
                # Case 1: single (or more that one with the same rate) advance on whole amount
                return advances[0].balance / advances[0].amount_currency

            else:
                # Case 2: one or more advances on partial amount
                # Case 3: two or more advances on the whole amount
                amount_done = sum(map(lambda r: r.quantity_done * r.purchase_line_id.price_unit, picking.move_ids))
                if not amount_done:
                    return picking.customs_declaration_currency_rate

                # add advanced amount part
                amount_total = 0
                amount_total_currency = 0

                for advance in advances:
                    if picking.purchase_currency_id.compare_amounts(amount_total_currency + advance.abs_amount_residual_currency, amount_done) >= 0:
                        amount_total += advance.abs_residual_balance * (amount_done - amount_total_currency) / advance.abs_amount_residual_currency
                        amount_total_currency = amount_done
                        break

                    amount_total += advance.abs_residual_balance
                    amount_total_currency += advance.abs_amount_residual_currency

                # add part by customs rate
                if company_currency.compare_amounts(amount_done, amount_total_currency) > 0:
                    amount_total += (amount_done - amount_total_currency) * picking.customs_declaration_currency_rate

                # compute currency rate
                return amount_total / amount_done

        else:

            # Case 4: without advances
            return picking.customs_declaration_currency_rate

    def _action_confirm(self, merge=True, merge_into=False):
        # switch off merging for import moves
        if any(self.mapped('picking_id.is_import')):
            merge = False

        # call super
        return super()._action_confirm(merge=merge, merge_into=merge_into)

    def _get_price_unit(self):
        self.ensure_one()

        if self.picking_id and self.picking_id.is_import:
            # if it's adjustment - return corrected price unit
            if self.import_adjustment_to_move_id:
                return self.price_unit / (self.product_qty or 1.0)

            # else - compute unit price
            price_unit = self.get_import_price_unit()
            self.price_unit = price_unit
            return price_unit

        else:
            return super()._get_price_unit()

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        self.ensure_one()

        # call super
        res = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)

        # check import SVL
        if svl_id:
            svl = self.env['stock.valuation.layer'].browse(svl_id)

            if svl and not svl.account_move_line_id and svl.stock_move_id and svl.stock_move_id.purchase_line_id and svl.stock_move_id.purchase_line_id.order_is_import:
                currency = svl.stock_move_id.purchase_line_id.currency_id
                if self.import_adjustment_to_move_id:
                    currency_rate = (svl.stock_move_id.price_unit / (svl.stock_move_id.product_qty or 1.0)) / (svl.stock_move_id.purchase_line_id.price_unit or 1.0)
                else:
                    currency_rate = svl.stock_move_id.get_svl_import_currency_rate()
                res['credit_line_vals']['amount_currency'] = currency.round(res['credit_line_vals']['balance'] / currency_rate)
                res['debit_line_vals']['amount_currency'] = currency.round(res['debit_line_vals']['balance'] / currency_rate)

        # return result
        return res
