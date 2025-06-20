from odoo import fields, models, api


class AccountMoveVatLine(models.Model):
    _name = 'account.move.vat.line'
    _description = "VAT invoice lines"
    _order = 'sequence, id'

    move_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='cascade',
        string="Journal Entry",
        required=True,
        readonly=True,
        index=True,
    )
    move_type = fields.Selection(
        related='move_id.move_type',
    )
    currency_id = fields.Many2one(
        related='move_id.company_currency_id',
    )
    company_id = fields.Many2one(
        related='move_id.company_id',
    )

    sequence = fields.Integer(
        default=10,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
    )
    uktzed_code_id = fields.Many2one(
        related='product_id.uktzed_code_id',
        string="UKTZED Code",
    )
    dkpp_code_id = fields.Many2one(
        related='product_id.dkpp_code_id',
        string="DKPP Code",
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
    )

    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        ondelete='restrict',
        compute='_compute_product_uom_id',
        store=True,
        readonly=False,
        precompute=True,
        string="Unit of Measure",
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    quantity = fields.Float(
        string="Quantity",
        required=True,
        digits='VAT quantity',
        default=1,
    )

    price_unit = fields.Float(
        string="Unit Price",
        digits="Product Price",
    )

    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
    )

    total_manual = fields.Monetary(
        string="Total edited",
    )

    total = fields.Monetary(
        string="Total",
        compute='_compute_total',
        inverse='_inverse_total',
        store=True,
    )

    vat_tax_id = fields.Many2one(
        comodel_name='account.tax',
        domain=[('tax_group_id.is_vat', '=', True)],
        string="VAT tax",
        required=True,
    )

    tax_before_vat_ids = fields.Many2many(
        comodel_name='account.tax',
        domain=[('tax_group_id.is_vat', '!=', True)],
        string="Other taxes",
    )

    vat_amount = fields.Monetary(
        string="VAT",
        compute='_compute_amount',
        store=True,
    )

    price_without_vat = fields.Monetary(
        string="Price without VAT",
        compute='_compute_without_vat',
    )

    total_without_vat = fields.Monetary(
        string="Total without VAT",
        compute='_compute_without_vat',
        inverse='_inverse_total_without_vat',
    )

    vat_base = fields.Monetary(
        string="VAT base",
        compute='_compute_vat_base',
    )

    adjustment_num_line_vat_invoice = fields.Integer(
        string="Line number to be adjusted",
    )
    adjustment_cause_type = fields.Selection(
        selection=[
            ('quantity', "Quantity Adjustment"),
            ('price', "Price Adjustment"),
        ],
        string="Cause Type Adjustment",
        default='quantity',
        copy=False,
    )
    adjustment_reason_type = fields.Selection(
        selection=[
            ('101', "101 - price change"),
            ('102', "102 - quantity change"),
            ('103', "103 - return of goods or advance payments"),
            ('104', "104 - change of nomenclature"),
            ('201', "201 - adjustments to the consolidated tax invoice drawn up in accordance with clause 198.5 of the TCU"),
            ('202', "202 - adjustments to the consolidated tax invoice drawn up in accordance with clause 199.1 of the TCU"),
            ('203', "203 - adjustments to the consolidated tax invoice drawn up in accordance with paragraph 11 of clause 201.4 of the TCU"),
            ('204', "204 - adjustment of a tax invoice drawn up in the course of a transaction for the free supply of goods/services"),
            ('301', "301 - correction of an error (clause 24 of the Procedure for filling out a tax invoice)"),
        ],
        string="Reason Code",
        copy=False,
    )
    adjustment_group = fields.Char(
        string="Adjustment group #",
    )
    name = fields.Char(
        string="Label",
        compute='_compute_name',
        store=True,
        readonly=False,
        precompute=True,
    )
    benefit_code_id = fields.Many2one(
        comodel_name='account.benefit_code',
        string="Benefit Code",
    )

    @api.depends('quantity', 'currency_id', 'vat_tax_id', 'total', 'tax_before_vat_ids', 'discount')
    def _compute_amount(self):
        for record in self:
            if record.vat_tax_id:
                taxes = record.tax_before_vat_ids + record.vat_tax_id
                dsc = (100 - (record.discount or 0))/100
                res = taxes.compute_all(price_unit=record.price_unit * dsc, quantity=record.quantity)
                vat_rec = next(x for x in res['taxes'] if x['id'] == record.vat_tax_id.id)
                record.vat_amount = vat_rec['amount']
            else:
                record.vat_amount = 0

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and line.move_id.move_type in ('vat_invoice', 'vat_adjustment_invoice'):
                taxes = line.product_id.taxes_id.filtered_domain([
                    ('company_id', '=', line.move_id.company_id.id),
                    ('type_tax_use', '=', 'sale'),
                    ('tax_group_id.is_vat', '=', True),
                ])
                if taxes:
                    line.vat_tax_id = taxes[0]
                    line.tax_before_vat_ids = line.product_id.taxes_id - taxes[0]
                else:
                    line.tax_before_vat_ids = line.product_id.taxes_id

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if line.move_id.partner_id.lang:
                product = line.product_id.with_context(lang=line.move_id.partner_id.lang)
            else:
                product = line.product_id

            values = []
            if product.partner_ref:
                values.append(product.partner_ref)
            if product.description_sale:
                values.append(product.description_sale)
            line.name = '\n'.join(values)

    @api.depends('quantity', 'price_unit', 'total_manual', 'discount')
    def _compute_total(self):
        for record in self:
            if record.price_unit:
                dsc = (100 - (record.discount if record.discount else 0))/100
                total = record.quantity * record.price_unit * dsc
                if total * 1.01 > record.total_manual > total * 0.99:
                    record.total = record.total_manual
                else:
                    record.total = total
                    record.total_manual = total
            else:
                record.total = 0
                record.total_manual = 0

    def _inverse_total(self):
        for record in self:
            record.total_manual = record.total

    @api.depends('price_unit', 'vat_tax_id', 'total')
    def _compute_without_vat(self):
        for record in self:
            if record.vat_tax_id and record.quantity and record.vat_tax_id.price_include:
                record.total_without_vat = record.total - record.vat_amount
                record.price_without_vat = record.total_without_vat / record.quantity
            else:
                record.total_without_vat = record.total
                record.price_without_vat = record.price_unit

    @api.onchange('total_without_vat')
    def _inverse_total_without_vat(self):
        for rec in self:
            if rec.move_id.move_type in ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice'):
                rec.price_unit = rec.total_without_vat
                rec.quantity = 1

    @api.depends('vat_tax_id', 'tax_before_vat_ids', 'discount', 'price_unit', 'quantity')
    def _compute_vat_base(self):
        for record in self:
            if record.vat_tax_id:
                taxes = record.tax_before_vat_ids + record.vat_tax_id
                dsc = (100 - (record.discount or 0)) / 100
                tax_calcs = taxes.compute_all(price_unit=record.price_unit * dsc, quantity=record.quantity)
                vat_calcs = next(x for x in tax_calcs['taxes'] if x['id'] == record.vat_tax_id.id)
                record.vat_base = vat_calcs['base']
            else:
                record.vat_base = 0
