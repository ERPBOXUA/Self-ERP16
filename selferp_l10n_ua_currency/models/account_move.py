from odoo import api, models, fields, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='vendor_bill_id',
        string="Stock Pickings",
    )
    stock_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        compute='_compute_stock_picking_id',
        string="Stock Picking",
    )

    is_import_vendor_bill = fields.Boolean(
        string="Import",
        default=False,
    )
    can_be_import_vendor_bill = fields.Boolean(
        compute='_compute_can_be_import_vendor_bill',
    )
    import_available_advance_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_import_available_advance_ids',
    )
    import_stored_advance_ids = fields.Many2many(
        comodel_name='account.move.line',
        relation='account_move_import_advance_rel',
        domain="[('id', 'in', import_available_advance_ids)]",
        copy=False,
    )
    import_advances_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_import_advances_ids',
    )

    is_customs_declaration = fields.Boolean(
        string="Export",
        default=False,
        states={'posted': [('readonly', True)]},
    )

    # To use in UI form
    can_be_cd = fields.Boolean(
        string="Can be Export Down Payment",
        compute='_compute_can_be_cd',
    )

    cd_currency_rate = fields.Float(
        string="Currency Rate",
        digits=(16, 4),
        states={'posted': [('readonly', True)]},
    )

    cd_date = fields.Date(
        states={'posted': [('readonly', True)]},
    )

    # to use in filter domain in UI
    cd_can_be_prepayment_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_can_be_prepayment_ids',
    )

    cd_prepayment_ids = fields.Many2many(
        comodel_name='account.move.line',
        string="Advances",
        domain="[('id', 'in', cd_can_be_prepayment_ids)]",
        copy=False,
    )

    @api.depends('stock_picking_ids')
    def _compute_stock_picking_id(self):
        for record in self:
            record.stock_picking_id = record.stock_picking_ids and record.stock_picking_ids[0] or None

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_can_be_import_vendor_bill(self):
        for rec in self:
            rec.can_be_import_vendor_bill = rec.currency_id != rec.company_id.currency_id and rec.move_type == 'in_invoice'

    @api.depends(
        'is_import_vendor_bill',
        'currency_id',
        'date',
        'partner_id',
        'partner_id.property_account_receivable_id',
    )
    def _compute_import_available_advance_ids(self):
        for record in self:
            if record.is_import_vendor_bill:
                record.import_available_advance_ids = record.env['account.move.line'].search([
                    ('currency_id.id', '=', record.currency_id.id),
                    ('account_id.id', '=', record.partner_id.property_account_payable_id.id),
                    ('partner_id.id', '=', record.partner_id.id),
                    ('reconciled', '=', False),
                    ('date', '<=', record.date),
                    ('balance', '>', 0),
                ])
            else:
                record.import_available_advance_ids = None

    @api.depends('is_import_vendor_bill', 'stock_picking_ids', 'import_stored_advance_ids')
    def _compute_import_advances_ids(self):
        for record in self:
            if record.is_import_vendor_bill and record.stock_picking_id:
                # we need it to simplify dependencies to prevent Odoo warning
                stock_picking_id = record.stock_picking_ids and record.stock_picking_ids[0] or None
                record.import_advances_ids = stock_picking_id.advance_line_ids if stock_picking_id else None

            elif record.is_import_vendor_bill:
                record.import_advances_ids = record.import_stored_advance_ids

            else:
                record.import_advances_ids = None

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_can_be_cd(self):
        for rec in self:
            rec.can_be_cd = rec.currency_id != rec.company_id.currency_id and rec.move_type == 'out_invoice'

    @api.depends(
        'is_customs_declaration',
        'cd_date',
        'currency_id',
        'company_id.currency_id',
        'can_be_cd',
        'partner_id.property_account_receivable_id',
        'partner_id',
    )
    def _compute_can_be_prepayment_ids(self):
        for rec in self:
            if rec.can_be_cd and rec.cd_date:
                rec.cd_can_be_prepayment_ids = rec.env['account.move.line'].search([
                    ('currency_id.id', '=', rec.currency_id.id),
                    ('account_id.id', '=', rec.partner_id.property_account_receivable_id.id),
                    ('partner_id.id', '=', rec.partner_id.id),
                    ('reconciled', '=', False),
                    ('date', '<=', rec.cd_date),
                    ('balance', '<', 0),
                ])
            else:
                rec.cd_can_be_prepayment_ids = rec.env['account.move.line'].browse()

    @api.depends('cd_prepayment_ids')
    def _compute_cd_prepayment_ui_ids(self):
        for line in self:
            line.cd_prepayment_ui_ids = line.cd_prepayment_ids

    @api.onchange('is_customs_declaration', 'is_import_vendor_bill', 'invoice_date')
    def _onchange_invoice_date(self):
        for record in self:
            if record.is_customs_declaration or record.is_import_vendor_bill:
                record.cd_date = record.invoice_date

    @api.onchange('is_customs_declaration', 'is_import_vendor_bill', 'cd_date')
    def _onchange_is_customs_declaration(self):
        for record in self:
            if record.is_customs_declaration or record.is_import_vendor_bill:
                if not record.cd_date:
                    record.cd_date = record.invoice_date or record.date
                rate = self.env['res.currency']._get_conversion_rate(
                    record.company_id.currency_id,
                    record.currency_id,
                    record.company_id,
                    record.cd_date,
                )
                if rate:
                    record.cd_currency_rate = 1 / rate
                else:
                    record.cd_currency_rate = None
            else:
                record.cd_date = None
                record.cd_currency_rate = None

    @api.model_create_multi
    def create(self, vals_list):
        new_records = super().create(vals_list)

        # update import currency rate
        for record in new_records:
            if record.is_import_vendor_bill and not record.cd_date:
                record.cd_date = record.invoice_date or record.date
                record._onchange_is_customs_declaration()

        return new_records

    def action_post(self):
        res = False

        for record in self:
            # Is Export
            if record.is_customs_declaration:
                record = record.with_context(disable_create_currency_exchange=True, no_exchange_difference=True)
                res = super(AccountMove, record).action_post()
                for line in record.cd_prepayment_ids.sorted('date'):
                    record.js_assign_outstanding_line(line.id)

            # Is Import
            elif record.is_import_vendor_bill:
                record = record.with_context(disable_create_currency_exchange=True, no_exchange_difference=True)
                res = super(AccountMove, record).action_post()
                for line in record.import_advances_ids.sorted('date'):
                    record.js_assign_outstanding_line(line.id)

            else:
                res = super(AccountMove, record).action_post()

        return res

    def action_show_stock_picking(self):
        self.ensure_one()
        if self.stock_picking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Picking"),
                'res_model': self.stock_picking_id._name,
                'res_id': self.stock_picking_id.id,
                'view_mode': 'form',
            }

    def get_currency_rate_with_advances(self):
        self.ensure_one()

        total = sum(self.line_ids.mapped('price_total'))
        if self.currency_id.is_zero(total):
            return 1

        advances = (
            (self.is_customs_declaration and self.cd_prepayment_ids)
            or (self.is_import_vendor_bill and self.import_advances_ids)
        )
        if not advances:
            return 1

        advance_amount_currency = sum(advances.mapped('abs_amount_residual_currency'))
        if total >= advance_amount_currency:
            rest_amount = (total - advance_amount_currency) * self.cd_currency_rate
            advance_amount = sum(advances.mapped('abs_residual_balance'))
            return (advance_amount + rest_amount) / total

        else:
            sum_balance = 0
            sum_advance = 0

            for advance in advances.sorted(key=lambda p: (p.date, p.id)):
                if advance.abs_amount_residual_currency + sum_balance > total:
                    amount = total - sum_advance
                    sum_balance += advance.abs_residual_balance / advance.abs_amount_residual_currency * amount
                    break

                else:
                    sum_balance += advance.abs_residual_balance
                    sum_advance += advance.abs_amount_residual_currency

            return sum_balance / total

    def _get_accounting_date(self, invoice_date, has_tax):
        if self.stock_picking_id.is_import:
            return invoice_date

        return super()._get_accounting_date(invoice_date, has_tax)

    def _post(self, soft=True):
        res = super()._post(soft)

        if self.statement_line_id:
            self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()

        return res
