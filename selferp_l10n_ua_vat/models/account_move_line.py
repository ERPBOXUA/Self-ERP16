from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    linked_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        index=True,
        string="Sale Order",
        help="Sale order linked with this journal entry",
    )
    linked_purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        index=True,
        string="Linked Purchase Order",
        help="Purchase order linked with this journal entry",
    )

    amount_first_event = fields.Monetary(
        string="First Event Amount",
        compute='_compute_amount_first_event',
    )

    vat_invoice_id = fields.Many2one(
        string="VAT invoice",
        comodel_name='account.move',
        ondelete='set null',
        index=True,
        copy=False,
    )
    first_event_vat_invoice_id = fields.Many2one(
        string="First Event VAT invoice",
        comodel_name='account.move',
        ondelete='set null',
        compute='_compute_vat_invoice',
        compute_sudo=True,
        store=True,
        index=True,
        copy=False,
    )
    amount_vat_tax = fields.Monetary(
        string="VAT Amount",
        compute='_compute_amount_vat_tax',
        compute_sudo=True,
    )

    vat_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="VAT tax",
        compute='_compute_vat_tax',
        compute_sudo=True,
    )

    tax_before_vat_ids = fields.Many2one(
        comodel_name='account.tax',
        string="Other taxes",
        compute='_compute_vat_tax',
        compute_sudo=True,
    )

    vat_invoice_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="VAT invoice tax",
    )

    vat_first_event_move_id = fields.Many2one(
        comodel_name='account.move',
        string="VAT first event",
        ondelete='set null',
        copy=False,
    )

    def _compute_vat_tax(self):
        for record in self:
            vat = None
            taxes = self.env['account.tax'].browse()
            for tax in record.tax_ids:
                if tax.tax_group_id.is_vat:
                    vat = tax
                else:
                    taxes += tax
            record.vat_tax_id = vat
            record.tax_before_vat_ids = taxes

    def _compute_amount_first_event(self):
        for record in self:
            first_event = record._calc_first_event_by_move_line() if record.account_id.first_event else None
            record.amount_first_event = first_event and first_event['amount_first_event'] or 0.0

    @api.depends(
        'account_id',
        'account_id.first_event',
        'vat_invoice_id',
        'vat_first_event_move_id',
        'vat_invoice_id.first_event_vat_invoice_id',
    )
    def _compute_vat_invoice(self):
        for record in self:
            if record.vat_first_event_move_id:
                record.first_event_vat_invoice_id = record.vat_first_event_move_id
            elif record.account_id.first_event and record.vat_invoice_id:
                record.first_event_vat_invoice_id = self.env['account.move'].search(
                    [('first_event_vat_invoice_id', '=', record.vat_invoice_id.id)],
                    limit=1,
                )

            else:
                record.first_event_vat_invoice_id = None

    @api.depends('account_id', 'account_id.first_event', 'vat_invoice_id', 'vat_first_event_move_id')
    def _compute_amount_vat_tax(self):
        for record in self:
            if record.vat_first_event_move_id:
                if record.account_id.account_type == 'liability_payable':
                    acc_vat_confirmed = record.move_id.company_id.vat_account_confirmed_credit_id
                    record.amount_vat_tax = - sum(
                        record.vat_first_event_move_id.line_ids.filtered(lambda l: l.account_id == acc_vat_confirmed).mapped('balance')
                    )
                else:
                    record.amount_vat_tax = sum(record.vat_first_event_move_id.line_ids.mapped('debit'))
            elif record.account_id.first_event and record.vat_invoice_id:
                record.amount_vat_tax = record.vat_invoice_id.vat_line_tax
            else:
                record.amount_vat_tax = 0

    @api.depends('move_id', 'product_id', 'move_id.move_type')
    def _compute_display_type(self):
        for record in self.filtered(lambda r: not r.display_type and r.move_id and r.move_id.move_type == 'vat_invoice'):
            record.display_type = 'product' if record.product_id else 'tax'

        super()._compute_display_type()

    @api.depends('move_id.contract_id', 'account_id', 'linked_sale_order_id')
    @api.onchange('move_id', 'account_id', 'linked_sale_order_id')
    def _compute_contract_id(self):
        for record in self:
            if record.move_type in ('vat_invoice', 'vat_adjustment_invoice') and record.account_id.code == '643200':
                if record.move_id and record.move_id.contract_id:
                    record.contract_id = record.move_id.contract_id
                else:
                    record.contract_id = record.linked_sale_order_id and record.linked_sale_order_id.contract_id or None

            else:
                super(AccountMoveLine, record)._compute_contract_id()

    def _calc_first_event_by_move_line(self):
        self.ensure_one()
        return self.env['account.vat.calculations']._calc_first_event_by_move_line(self)

    @api.model_create_multi
    def create(self, values):
        lines = super().create(values)

        lines.check_linked_sale_order()
        lines.check_linked_purchase_order()

        return lines

    def write(self, values):
        res = super().write(values)

        if 'account_id' in values or 'statement_line_id' in values:
            self.check_linked_sale_order()
            self.check_linked_purchase_order()

        return res

    def check_linked_sale_order(self):
        for record in self:
            if record.move_type in ('vat_invoice', 'vat_adjustment_invoice') and record.account_id.code == '643200':
                record.linked_sale_order_id = record.move_id and record.move_id.vat_sale_order_id or None

            if record.payment_id:
                # linking with order was already done on payment create
                continue

            linked_sale_order_id = None

            if record.move_id.state == 'posted' and record.account_id and record.account_type == 'asset_receivable':
                if record.statement_line_id:
                    # check matched debit moves
                    if record.matched_debit_ids:
                        matched = record.matched_debit_ids.filtered(lambda r: r.credit_move_id == record and r.debit_move_id.linked_sale_order_id)
                        if len(matched) == 1:
                            linked_sale_order_id = matched.debit_move_id.linked_sale_order_id

                    # check matched credit moves
                    if not linked_sale_order_id and record.matched_credit_ids:
                        matched = record.matched_credit_ids.filtered(lambda r: r.debit_move_id == record and r.credit_move_id.linked_sale_order_id)
                        if len(matched) == 1:
                            linked_sale_order_id = matched.credit_move_id.linked_sale_order_id

                    # get from statement line
                    if not linked_sale_order_id:
                        linked_sale_order_id = record.statement_line_id.linked_sale_order_id

                else:
                    # get first sale order, since we limited to crete invoice from one sale order only
                    orders = record.move_id.mapped('line_ids.sale_line_ids.order_id')
                    if orders:
                        linked_sale_order_id = orders[0]

            # save changes
            if record.linked_sale_order_id != linked_sale_order_id:
                record.linked_sale_order_id = linked_sale_order_id

    def check_linked_purchase_order(self):
        for record in self:
            if record.payment_id:
                # linking with order was already done on payment create
                continue

            linked_purchase_order_id = None

            if record.move_id.state == 'posted' and record.account_id and record.account_type == 'liability_payable':
                if record.statement_line_id:
                    # check matched credit moves
                    if record.matched_credit_ids:
                        matched = record.matched_credit_ids.filtered(lambda r: r.debit_move_id == record and r.credit_move_id.linked_purchase_order_id)
                        if len(matched) == 1:
                            linked_purchase_order_id = matched.credit_move_id.linked_purchase_order_id

                    # check matched debit moves
                    if not linked_purchase_order_id and record.matched_debit_ids:
                        matched = record.matched_debit_ids.filtered(lambda r: r.credit_move_id == record and r.debit_move_id.linked_purchase_order_id)
                        if len(matched) == 1:
                            linked_purchase_order_id = matched.debit_move_id.linked_purchase_order_id

                    # get from statement line
                    if not linked_purchase_order_id:
                        linked_purchase_order_id = record.statement_line_id.linked_purchase_order_id

                else:
                    # get first purchase order, since we limited to crete invoice from one sale order only
                    orders = record.move_id.mapped('line_ids.purchase_line_id.order_id')
                    if orders:
                        linked_purchase_order_id = orders[0]

            # save changes
            if record.linked_purchase_order_id != linked_purchase_order_id:
                record.linked_purchase_order_id = linked_purchase_order_id

    def reconcile(self):
        res = super().reconcile()

        self.check_linked_sale_order()
        self.check_linked_purchase_order()

        vendor_reconcilable_moves = self.filtered(lambda ln: ln.move_id and ln.move_id.vat_vendor_reconcilable).mapped('move_id')
        if vendor_reconcilable_moves:
            vendor_reconcilable_moves._update_refs()

        return res

    def remove_move_reconcile(self):
        vendor_reconcilable_moves = self.filtered(lambda ln: ln.move_id and ln.move_id.vat_vendor_reconcilable).mapped('move_id')
        super().remove_move_reconcile()
        if vendor_reconcilable_moves:
            vendor_reconcilable_moves._update_refs()
