from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_move_id = fields.Many2one(
        comodel_name='stock.move',
        ondelete='restrict',
        string="Stock Move",
        copy=False,
    )

    customs_declaration_id = fields.Many2one(
        comodel_name='account.move',
    )

    abs_amount_residual_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_abs_amount_residual_currency',
    )

    abs_residual_balance = fields.Monetary(
        string="Amount Company Currency",
        currency_field='company_currency_id',
        compute='_compute_abs_residual_balance',
    )

    currency_rate_back = fields.Float(
        compute='_compute_currency_rate_back',
        digits=(16, 4),
    )

    @api.depends('amount_residual_currency')
    def _compute_abs_amount_residual_currency(self):
        for rec in self:
            rec.abs_amount_residual_currency = abs(rec.amount_residual_currency)

    @api.depends('amount_residual')
    def _compute_abs_residual_balance(self):
        for rec in self:
            rec.abs_residual_balance = abs(rec.amount_residual)

    @api.depends('currency_rate', 'amount_currency', 'balance')
    def _compute_currency_rate_back(self):
        for rec in self:
            if not rec.currency_id.is_zero(rec.amount_currency):
                rec.currency_rate_back = rec.balance / rec.amount_currency
            elif rec.currency_rate:
                rec.currency_rate_back = 1 / rec.currency_rate
            else:
                rec.currency_rate_back = None

    @api.depends(
        'currency_id',
        'company_id',
        'move_id.date',
        'move_id.is_customs_declaration',
        'move_id.cd_currency_rate',
        'move_id.cd_prepayment_ids.abs_amount_residual_currency',
        'move_id.cd_prepayment_ids.abs_residual_balance',
        'move_id.is_import_vendor_bill',
        'move_id.import_advances_ids',
        'amount_currency',
        'purchase_line_id',
        'purchase_line_id.order_is_import',
        'stock_move_id',
        'price_unit',
        'price_subtotal',
        'price_total',
    )
    def _compute_currency_rate(self):
        for record in self:
            move = record.move_id

            # check the whole bill is there any import line
            import_lines = move.line_ids.filtered(lambda r: r.purchase_line_id and r.purchase_line_id.order_is_import and r.stock_move_id)
            stock_pickings = import_lines.mapped('stock_move_id.picking_id')
            if len(stock_pickings) > 1:
                raise UserError(_("Multiple imports in a single move are not supported"))

            if import_lines:
                # compute currency rate
                stock_move = record.stock_move_id
                if stock_move:
                    if stock_move.import_adjustment_to_move_id:
                        # for adjustment line currency rate includes cost of quantity
                        # (for now equals to 1.0) by stock in company currency
                        # (already corrected previously in SVL) and difference
                        # between total cost by stock and amount total by bill
                        # in company currency
                        currency_rate_value = (stock_move.price_unit / (stock_move.product_qty or 1.0)) / (record.purchase_line_id.price_unit or 1.0)

                    else:
                        # compute rate for others stock moves based on stock cost:
                        # divide total cost by stock in company currency on
                        # amount total by bill in the currency
                        currency_rate_value = (
                            record.company_currency_id.round(stock_move.price_unit * stock_move.quantity_done) /
                            (record.currency_id.round(record.purchase_line_id.price_unit * record.quantity) or 1.0)
                        )

                else:
                    # any other lines (not linked with stock moves) have
                    # the currency rate by whole document because it's already
                    # adjusted
                    stock_move = import_lines.mapped('stock_move_id').filtered(lambda r: not r.import_adjustment_to_move_id)[0]
                    currency_rate_value = stock_move.get_import_currency_rate()

                # compute inverse currency rate
                record.currency_rate = 1 / currency_rate_value

            elif move.is_customs_declaration or move.is_import_vendor_bill:
                # compute currency rate
                if move.cd_prepayment_ids or record.move_id.import_advances_ids:
                    currency_rate_value = move.get_currency_rate_with_advances()
                    record.currency_rate = 1 / currency_rate_value
                elif move.cd_currency_rate:
                    record.currency_rate = 1 / move.cd_currency_rate
                else:
                    super(AccountMoveLine, record)._compute_currency_rate()

            else:
                super(AccountMoveLine, record)._compute_currency_rate()

    @api.model
    def _prepare_reconciliation_single_partial(self, debit_vals, credit_vals):
        """ We had to override this method for all currency operations,
            because we should pay attention at advances.

        :param debit_vals:
        :param credit_vals:
        :return:
        """
        debit_record = debit_vals.get('record')
        credit_record = credit_vals.get('record')

        company_currency = debit_vals['company'].currency_id
        remaining_debit_amount_curr = debit_vals['amount_residual_currency'] or 0
        remaining_credit_amount_curr = -(credit_vals['amount_residual_currency'] or 0)

        # if it's a currency operation with advance payment reconciliation -
        # reconcile it with advance payment rate instead of move currency rate
        if (
            debit_record
            and debit_vals['currency'] != company_currency
            and not debit_vals['currency'].is_zero(remaining_debit_amount_curr)
            and credit_record
            and not credit_vals['currency'].is_zero(remaining_credit_amount_curr)
            and (
                (debit_record.move_id.is_customs_declaration and debit_record.move_id.cd_prepayment_ids)
                or
                (credit_record.move_id.is_import_vendor_bill and credit_record.move_id.import_advances_ids)
            )
        ):
            # check amounts
            partial_debit_amount = debit_vals['amount_residual']
            partial_credit_amount = -credit_vals['amount_residual']
            partial_amount = min(partial_debit_amount, partial_credit_amount)
            partial_amount_currency = min(remaining_debit_amount_curr, remaining_credit_amount_curr)

            # check fully reconciled
            compare_amounts = debit_vals['currency'].compare_amounts(remaining_debit_amount_curr, remaining_credit_amount_curr)
            debit_fully_matched = compare_amounts <= 0
            credit_fully_matched = compare_amounts >= 0

            # compute with correct currency rate
            # (exclude advance amounts which already reconciled)
            # in the other case currency rate will be wrong,
            # calculated as total (not residual) amount in currency
            # and company currency
            if credit_record not in debit_record.move_id.cd_prepayment_ids:
                partial_amount = partial_amount_currency * (debit_vals['amount_residual'] / debit_vals['amount_residual_currency'])

            # update debit/credit vals
            if not debit_fully_matched:
                debit_vals['amount_residual'] -= partial_amount
                debit_vals['amount_residual_currency'] -= partial_amount_currency
            else:
                debit_vals = None
            if not credit_fully_matched:
                credit_vals['amount_residual'] += partial_amount
                credit_vals['amount_residual_currency'] += partial_amount_currency
            else:
                credit_vals = None

            # return rest of debit/credit vals
            return {
                'debit_vals': debit_vals,
                'credit_vals': credit_vals,
                'partial_vals': {
                    'amount': partial_amount,
                    'debit_amount_currency': partial_amount_currency,
                    'credit_amount_currency': partial_amount_currency,
                    'debit_move_id': debit_record.id,
                    'credit_move_id': credit_record.id,
                },
            }

        # else - call super
        return super()._prepare_reconciliation_single_partial(debit_vals, credit_vals)

    def _create_reconciliation_partials(self):
        # put adjustment lines followed by adjusted lines
        # and stock valuation layer followed by linked line
        lines = self.browse()

        if len(self) > 1:
            while self:
                line = self[0]
                lines += line
                self -= line

                counterpart_lines = None
                if line.move_id.stock_move_id:
                    counterpart_lines = self.filtered(lambda r: r.stock_move_id == line.move_id.stock_move_id)
                elif line.stock_move_id:
                    counterpart_lines = self.filtered(lambda r: r.move_id and r.move_id.stock_move_id == line.stock_move_id)

                if counterpart_lines:
                    lines += counterpart_lines
                    self -= counterpart_lines
        else:
            lines = self

        # and then call super
        return super(AccountMoveLine, lines)._create_reconciliation_partials()

    def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None, **kwargs):
        if self._context.get('disable_create_currency_exchange'):
            # return an empty result
            return {
                'move_vals': {'line_ids': []},
                'to_reconcile': [],
            }

        else:
            return super()._prepare_exchange_difference_move_vals(amounts_list, company=company, exchange_date=exchange_date, **kwargs)

    def _apply_price_difference(self):
        if self._context.get('disable_create_currency_exchange'):
            return self.env['stock.valuation.layer'].sudo().browse(), self.env['account.move.line'].sudo().browse()
        else:
            return super()._apply_price_difference()
