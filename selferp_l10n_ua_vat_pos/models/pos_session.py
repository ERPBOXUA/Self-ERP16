from odoo import models, fields, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    vat_invoice_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="VAT Invoice",
    )
    vat_state = fields.Selection(
        selection=[
            ('taxed', "Taxed"),
        ],
        compute='_compute_vat_state',
        string="VAT State",
    )
    vat_invoice_total = fields.Monetary(
        string="Total VAT Invoice",
        compute='_compute_vat_invoice_total',
    )

    def _compute_vat_invoice_total(self):
        for rec in self:
            rec.vat_invoice_total = rec.vat_invoice_id.vat_line_total

    def _compute_vat_state(self):
        for record in self:
            record.vat_state = 'taxed' if record.vat_invoice_id else None

    def action_create_vat_invoice(self):
        if self.filtered(lambda r: r.state != 'closed'):
            raise UserError(_("A VAT invoice can be created only from a session in Closed state"))
        if self.filtered(lambda r: r.vat_invoice_id):
            raise UserError(_("A VAT invoice has already been generated for session"))

        so_info = self._so_info_from_session()
        invoice = self.env['account.vat.calculations'].create_vat_invoice(
            move=None,
            first_event=so_info['total'],
            so_info=so_info,
            partner=self.config_id.vat_partner_id,
            ref=', '.join(self.mapped('name')),
        )
        invoice.vat_invoice_no_obligation = True
        self.write({
            'vat_invoice_id': invoice.id,
        })

    def action_show_vat_invoice(self):
        self.ensure_one()
        if self.vat_invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.vat_invoice_id._name,
                'res_id': self.vat_invoice_id.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {
                    'default_move_type': self.vat_invoice_id.move_type,
                }
            }

    @classmethod
    def _get_ua_vat_id(cls, taxes):
        for tax in taxes.filtered(lambda l: l.tax_group_id.is_vat):
            return tax.id
        return None

    @classmethod
    def _get_line_vat(cls, line):
        for tax in line.tax_ids.filtered(lambda l: l.tax_group_id.is_vat):
            return tax._compute_amount(line.price_subtotal_incl, line.price_unit)
        return 0

    def _so_info_from_session(self):
        total = 0
        products = []
        prod_dict = {}

        for order_line in self.mapped('order_ids.lines'):
            prod_key = (order_line.product_id.id, order_line.price_unit, order_line.discount)

            if prod_key in prod_dict:
                prod_item = prod_dict[prod_key]

            else:
                vat_tax_id = self._get_ua_vat_id(order_line.tax_ids)
                if vat_tax_id:
                    prod_item = {
                        'id': order_line.product_id.id,
                        'name': order_line.name,
                        'product_uom': order_line.product_uom_id.id,
                        'product_uom_qty': 0,
                        'price_total': 0,
                        'price_unit': order_line.price_unit,
                        'discount': order_line.discount,
                        'before_vat_ids': list(filter(lambda tax: tax != vat_tax_id, order_line.tax_ids.ids)),
                        'tax_id': vat_tax_id,
                        'vat': 0,
                        'vat_payed': 0,
                        'vat_qty': 0,
                    }
                    prod_dict[prod_key] = prod_item
                    products.append(prod_item)
                else:
                    prod_item = None
            if prod_item:
                prod_item['product_uom_qty'] += order_line.qty
                prod_item['price_total'] += order_line.price_subtotal_incl
                total += order_line.price_subtotal_incl
                prod_item['vat'] += self._get_line_vat(order_line)

        return {
            'products': products,
            'total': total,
        }



