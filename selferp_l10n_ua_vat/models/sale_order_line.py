from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    vat_invoice_qty = fields.Float(
        string="Quantity in VAT invoices",
        digits='VAT quantity',
        compute='_compute_vat_invoice_qty',
    )

    @api.depends(
        'order_id.vat_invoices_summary',
        'product_id',
        'product_uom',
        'price_unit',
        'discount',
        'tax_id',
    )
    def _compute_vat_invoice_qty(self):
        for rec in self:
            if rec.display_type or not rec.order_id:
                rec.vat_invoice_qty = False
            else:
                summary = rec.order_id.get_line_summary(rec)
                if summary:
                    rec.vat_invoice_qty = summary['qty']
                else:
                    rec.vat_invoice_qty = False

    def get_ua_vat(self):
        self.ensure_one()
        tax = self.get_ua_vat_tax()
        if not tax:
            return 0
        dsc = (100 - (self.discount or 0))/100
        tax_calc = self.tax_id.compute_all(price_unit=self.price_unit * dsc, quantity=self.product_uom_qty)
        vat_calc = next(x for x in tax_calc['taxes'] if x['id'] == tax.id)
        return vat_calc['amount']

    def get_ua_vat_tax(self):
        self.ensure_one()
        for tax in self.tax_id.filtered(lambda l: l.tax_group_id.is_vat):
            return tax
        return None

    def get_taxes_before_ua_vat(self):
        self.ensure_one()
        vat = self.get_ua_vat_tax()
        if vat:
            return self.tax_id - vat
        return self.tax_id
