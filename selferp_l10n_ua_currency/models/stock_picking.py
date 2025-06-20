from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_import = fields.Boolean(related='purchase_id.is_import')
    purchase_currency_id = fields.Many2one(related='purchase_id.currency_id')

    customs_declaration_date = fields.Date(
        string="Customs Declaration Date",
        default=lambda self: fields.Date.today(),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    customs_declaration_currency_rate = fields.Float(
        string="Customs Declaration Currency Rate",
        compute='_compute_customs_declaration_currency_rate',
        inverse='_inverse_customs_declaration_currency_rate',
        depends=['company_currency_id'],
        digits=(16, 4),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    customs_declaration_currency_rate_manual = fields.Float(
        digits=(16, 4),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency',
        default=lambda self: self.env.company.currency_id,
    )
    is_company_currency = fields.Boolean(
        compute='_compute_currency',
    )

    cd_can_be_advance_ids = fields.One2many(
        comodel_name='account.move.line',
        compute='_compute_can_be_advance_ids',
    )

    advance_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        string="Advance Payments",
        domain="[('id', 'in', cd_can_be_advance_ids)]",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )

    customs_declaration_line_ids = fields.One2many(
        comodel_name='stock.picking.customs_declaration.line',
        inverse_name='stock_picking_id',
        string="Customs Declaration",
    )

    landed_cost_ids = fields.Many2many(
        comodel_name='stock.landed.cost',
        compute='_compute_landed_cost',
    )
    landed_cost_count = fields.Integer(
        compute='_compute_landed_cost',
    )

    vendor_bill_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="Vendor Bill",
        copy=False,
    )

    cargo_customs_number = fields.Char(
        string="CCD number",
    )

    customs_fee = fields.Monetary(
        string="Customs Fee",
        currency_field='company_currency_id',
    )

    customs_cost = fields.Monetary(
        string="Customs Cost",
        currency_field='company_currency_id',
        default=0,
        required=True,
    )

    customs_duty_rate = fields.Float(
        string="Customs Duty Rate",
        default=0,
        required=True,
    )

    customs_duty_amount = fields.Monetary(
        string="Customs Duty Amount",
        currency_field='company_currency_id',
        compute='_compute_customs_amount',
    )

    customs_duty_UKTZED = fields.Boolean(
        string="Customs Duty UKTZED",
        default=False,
    )

    excise_duty_rate = fields.Float(
        string="Excise Duty rate",
        default=0,
        required=True,
    )

    excise_duty_amount = fields.Monetary(
        string="Excise Duty",
        currency_field='company_currency_id',
        compute='_compute_customs_amount',
    )

    vat_rate = fields.Float(
        string="VAT rate",
        default=20,
        required=True,
    )
    vat_amount = fields.Monetary(
        string="VAT amount",
        currency_field='company_currency_id',
        compute='_compute_customs_amount',
    )

    include_vat_to_cost = fields.Boolean(
        string="Include VAT to cost",
        default=True,
        required=True,
    )

    @api.depends('customs_duty_rate', 'excise_duty_rate', 'vat_rate')
    @api.onchange('customs_duty_rate', 'excise_duty_rate', 'vat_rate')
    def _compute_customs_amount(self):
        for record in self:
            record.customs_duty_amount = record.customs_cost * record.customs_duty_rate / 100
            record.excise_duty_amount = record.customs_cost * record.excise_duty_rate / 100
            record.vat_amount = (record.customs_cost + record.excise_duty_amount + record.customs_duty_amount) * record.vat_rate / 100

    def _compute_currency(self):
        for record in self:
            record.company_currency_id = record.company_id.currency_id
            record.is_company_currency = record.purchase_currency_id == record.company_id.currency_id

    @api.depends('company_id', 'customs_declaration_date', 'purchase_currency_id')
    @api.onchange('company_id', 'customs_declaration_date', 'purchase_currency_id')
    def _compute_customs_declaration_currency_rate(self):
        for record in self:
            customs_declaration_currency_rate = record.customs_declaration_currency_rate_manual

            if not customs_declaration_currency_rate:
                if record.customs_declaration_date and record.purchase_currency_id and record.company_currency_id and record.company_id:
                    rate = record.company_currency_id._get_conversion_rate(
                        record.company_currency_id,
                        record.purchase_currency_id,
                        record.company_id,
                        record.customs_declaration_date,
                    )
                    if rate:
                        customs_declaration_currency_rate = 1 / rate
                else:
                    customs_declaration_currency_rate = 1

            record.customs_declaration_currency_rate = customs_declaration_currency_rate

    def _inverse_customs_declaration_currency_rate(self):
        for record in self:
            record.customs_declaration_currency_rate_manual = record.customs_declaration_currency_rate

    def _compute_landed_cost(self):
        StockLandedCost = self.env['stock.landed.cost']
        for record in self:
            record.landed_cost_ids = StockLandedCost.search([('picking_ids', 'in', record.ids)])
            record.landed_cost_count = len(record.landed_cost_ids)

    @api.depends(
        'is_import',
        'customs_declaration_date',
        'purchase_currency_id',
        'partner_id.property_account_receivable_id',
        'partner_id',
    )
    def _compute_can_be_advance_ids(self):
        for rec in self:
            if rec.is_import and rec.customs_declaration_date:
                rec.cd_can_be_advance_ids = rec.env['account.move.line'].search(
                    [
                        ('currency_id.id', '=', rec.purchase_currency_id.id),
                        ('account_id.id', '=', rec.partner_id.property_account_payable_id.id),
                        ('partner_id.id', '=', rec.partner_id.id),
                        ('reconciled', '=', False),
                        ('date', '<=', rec.customs_declaration_date),
                        ('balance', '>', 0),
                    ],
                    order='date',
                )
            else:
                rec.cd_can_be_advance_ids = rec.env['account.move.line'].browse()

    def action_create_landed_cost(self):
        self.ensure_one()

        # prepare landed cost lines
        cost_lines = []
        for line in self.customs_declaration_line_ids:
            accounts_data = line.product_id.product_tmpl_id.get_product_accounts()
            cost_lines.append(Command.create({
                'name': line.description or line.product_id.name,
                'product_id': line.product_id.id,
                'price_unit': line.amount,
                'split_method': line.product_id.product_tmpl_id.split_method_landed_cost or 'equal',
                'account_id': accounts_data['stock_input'] and accounts_data['stock_input'].id or None,
            }))

        # create landed cost
        landed_cost = self.env['stock.landed.cost'].create({
            'target_model': 'picking',
            'picking_ids': [Command.link(self.id)],
            'date': self.customs_declaration_date,
            'cost_lines': cost_lines,
        })

        # open landed cost record
        return {
            'type': 'ir.actions.act_window',
            'name': _("Landed Cost"),
            'res_model': landed_cost._name,
            'res_id': landed_cost.id,
            'view_mode': 'form',
        }

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
                    ('picking_ids', 'in', self.ids),
                ],
                'view_mode': 'tree,form',
            }

    def action_show_vendor_bill(self):
        self.ensure_one()
        if self.vendor_bill_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Vendor Bill"),
                'res_model': self.vendor_bill_id._name,
                'res_id': self.vendor_bill_id.id,
                'view_mode': 'form',
            }

    def action_confirm(self):
        # check rights
        if self.filtered(lambda r: r.is_import) and not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_("Only account manager can confirm customs declaration."))

        # confirm stock picking
        return super().action_confirm()

    def button_validate(self):
        # check linked advances
        if self.filtered(lambda r: r.is_import and r.advance_line_ids.filtered(lambda a: a.reconciled)):
            raise UserError(_("Cannot confirm customs declaration with advances already reconciled."))

        # SVL will be created by unit price in company currency, in the other hand
        # we have the total amount and quantity in purchase currency (and
        # currency rate as well).
        # It may cause a difference (in cents) between an SVL and vendor bill.
        # As a result, not all lines will be fully reconciled.
        # So, check the amount difference by SVL and modify or create additional
        # stock moves here if it's needed.

        # Always use 1.0 as quantity adjustment:
        # - if quantity > 1 - reduce the stock move quantity and add additional line with quantity = 1
        # - if quantity = 1 - just let it as is, because there is no difference with SVL price unit
        # - if quantity < 1 - @TODO let it as is, we just can't get solution for all 100% cases because of precision
        quantity_adjustment = 1.0

        for picking in self:
            if not picking.is_import or not picking.move_ids:
                continue

            company_currency = picking.company_currency_id
            move_updates = []

            for move in picking.move_ids:
                # check each stock move
                if move.purchase_line_id and float_compare(move.quantity_done, quantity_adjustment, precision_rounding=move.product_uom.rounding) > 0:
                    # compute amounts
                    currency = move.purchase_line_id.currency_id
                    currency_rate = move.get_import_currency_rate()
                    amount_total = currency.round(move.quantity_done * move.purchase_line_id.price_unit)
                    amount_total_company_currency = company_currency.round(amount_total * currency_rate)
                    adjusted_price_unit = company_currency.round(move.purchase_line_id.price_unit * currency_rate)
                    amount_total_company_currency_svl = company_currency.round(adjusted_price_unit * move.quantity_done)

                    # check the amount difference in company currency
                    amount_difference = company_currency.round(amount_total_company_currency - amount_total_company_currency_svl)
                    if not company_currency.is_zero(amount_difference):
                        # if there is some difference - reduce the stock move quantity
                        move_updates.append(Command.update(move.id, {
                            'product_uom_qty': move.product_qty - quantity_adjustment,
                            'quantity_done': move.quantity_done - quantity_adjustment,
                            'price_unit': adjusted_price_unit,
                        }))

                        # and create a new one with quantity 1.0
                        new_move_vals = move.purchase_line_id._prepare_stock_move_vals(
                            picking,
                            adjusted_price_unit + amount_difference,
                            quantity_adjustment,
                            move.product_uom,
                        )
                        new_move_vals.update({
                            'import_adjustment_to_move_id': move.id,
                            'name': move.name + ' [' + _("Import Adjustment") + ']',
                            'quantity_done': quantity_adjustment,
                        })
                        move_updates.append(Command.create(new_move_vals))

            # apply updates
            if move_updates:
                picking.write({'move_ids': move_updates})
                picking.move_ids._action_confirm()._action_assign()

        # confirm stock picking
        result = super().button_validate()

        # create and confirm a vendor bill for import with advances
        if result is True:
            for record in self.filtered(lambda r: r.is_import and r.advance_line_ids):
                vendor_bill = record._create_import_vendor_bill()
                vendor_bill.action_post()

        # return confirm result
        return result

    def allocate_customs_amount(self):
        self.ensure_one()

        sum_cost = sum(self.move_ids.mapped('customs_declaration_cost'))
        if sum_cost == 0:
            raise UserError(_("No customs declaration cost found. Change count or validate it."))

        rest = self.customs_cost
        for record in self.move_ids:
            record.customs_cost = record.customs_declaration_cost * self.customs_cost / sum_cost
            rest -= record.customs_cost
            if record == self.move_ids[-1]:
                record.customs_cost += rest
        rest_duty_cost = self.customs_duty_amount
        rest_excise_cost = self.excise_duty_amount
        rest_vat_cost = self.vat_amount
        vat_sum = 0
        if self.customs_cost == 0:
            raise UserError(_("Customs cost should be greater than 0."))
        rest_customs_fee = self.customs_fee
        if self.customs_duty_UKTZED:
            customs_dt_amount = 0
        else:
            customs_dt_amount = self.customs_duty_amount
        for record in self.move_ids:
            if self.customs_duty_UKTZED:
                if record.product_id.uktzed_code_id and record.product_id.uktzed_code_id.import_duty_rate_full:
                    try:
                        rate = float(record.product_id.uktzed_code_id.import_duty_rate_full.replace(',', '.'))
                    except ValueError:
                        raise UserError(_("UKTZED rate full is not a number."))
                    record.customs_duty_amount = self.company_currency_id.round(record.customs_cost * rate / 100)
                    customs_dt_amount += record.customs_duty_amount
                else:
                    raise UserError(_("No UKTZED code or customs duty rate found."))
            else:
                record.customs_duty_amount = self.company_currency_id.round(record.customs_cost * self.customs_duty_rate / 100)
            record.excise_duty_amount = self.company_currency_id.round(record.customs_cost * self.excise_duty_rate / 100)
            record.customs_fee = self.company_currency_id.round(record.customs_cost * self.customs_fee / self.customs_cost)
            record.vat_amount = self.company_currency_id.round((record.customs_cost + record.customs_duty_amount + record.excise_duty_amount) * self.vat_rate / 100)
            rest_duty_cost -= record.customs_duty_amount
            rest_excise_cost -= record.excise_duty_amount
            rest_vat_cost -= record.vat_amount
            rest_customs_fee -= record.customs_fee
            if record == self.move_ids[-1]:
                if not self.customs_duty_UKTZED:
                    record.customs_duty_amount += rest_duty_cost
                    record.vat_amount += rest_vat_cost
                record.excise_duty_amount += rest_excise_cost
                record.customs_fee += rest_customs_fee

            vat_sum += record.vat_amount

        def _update_customs_declaration_lines(product_xml_id, amount):
            product = self.env.ref(product_xml_id)

            product_record = self.customs_declaration_line_ids.filtered(lambda r: r.product_id == product)

            if amount > 0:
                if product_record:
                    product_record.amount = amount
                else:
                    product_record = self.env['stock.picking.customs_declaration.line'].create({
                        'stock_picking_id': self.id,
                        'product_id': product.id,
                        'description': product.name,
                        'amount': amount,
                    })
                    self.customs_declaration_line_ids += product_record
            else:
                if product_record:
                    self.customs_declaration_line_ids -= product_record
                    product_record.unlink()

        _update_customs_declaration_lines('selferp_l10n_ua_currency.product_product_expense_duty', customs_dt_amount)
        _update_customs_declaration_lines('selferp_l10n_ua_currency.product_product_expense_excise_duty', self.excise_duty_amount)
        _update_customs_declaration_lines('selferp_l10n_ua_currency.product_product_expense_customs_duty', self.customs_fee)

        if self.include_vat_to_cost:
            _update_customs_declaration_lines('selferp_l10n_ua_currency.product_product_expense_vat', vat_sum)
        else:
            _update_customs_declaration_lines('selferp_l10n_ua_currency.product_product_expense_vat', 0)

    def _create_import_vendor_bill(self):
        self.ensure_one()

        # fill vendor bill lines
        lines = []
        for i, move in enumerate(self.move_ids):
            lines.append(Command.create({
                'sequence': 10 + i,
                'display_type': 'product',
                'name': '%s: %s' % (self.name, move.name),
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'quantity': move.quantity_done,
                'price_unit': move.purchase_line_id.price_unit,
                'tax_ids': None,

                'purchase_line_id': move.purchase_line_id.id,
                'stock_move_id': move.id,
            }))

        # prepare vendor bill values
        invoice_vals = self.purchase_id._prepare_invoice()
        invoice_vals.update({
            'invoice_date': self.customs_declaration_date,
            'invoice_line_ids': lines,
        })
        if self.is_import:
            invoice_vals.update({
                'cd_date': self.customs_declaration_date,
                'cd_currency_rate': self.customs_declaration_currency_rate,
            })

        # create a vendor bill
        self.vendor_bill_id = self.env['account.move'].with_company(invoice_vals['company_id']).create(invoice_vals)

        # return created vendor bill
        return self.vendor_bill_id
