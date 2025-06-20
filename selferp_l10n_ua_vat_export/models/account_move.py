from odoo import api, models, fields, Command, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    customs_declaration_vat_invoice_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        copy=False,
    )
    customs_declaration_customer_invoice_id = fields.Many2one(
        comodel_name='account.move',
        compute='_compute_customs_declaration_customer_invoice_id',
    )

    @api.depends('is_customs_declaration', 'customs_declaration_vat_invoice_id')
    def _compute_customs_declaration_customer_invoice_id(self):
        for record in self:
            record.customs_declaration_customer_invoice_id = self.search(
                [('customs_declaration_vat_invoice_id', '=', record.id)],
                limit=1,
            )

    def action_create_customs_declaration_vat_invoice(self):
        self.ensure_one()

        if self.is_customs_declaration and not self.customs_declaration_vat_invoice_id:
            self.customs_declaration_vat_invoice_id = self.create({
                'move_type': 'vat_invoice',
                'ref': self.name,
                'partner_id': self.partner_id and self.partner_id.id or None,
                'date': self.cd_date,
                'not_issued_to_customer': True,
                'reason_type': '07',
                'vat_line_ids': [
                    Command.create({
                        'product_id': l.product_id.id,
                        'quantity': l.quantity,
                        'product_uom_id': l.product_uom_id.id,
                        'price_unit': l.price_unit * self.cd_currency_rate,
                        'total': l.price_total * self.cd_currency_rate,
                        'vat_tax_id': l.vat_tax_id and l.vat_tax_id.id or None,
                    })
                    for l in self.invoice_line_ids if l.product_id
                ],
            })
            return self.action_show_customs_declaration_vat_invoice()

    def action_show_customs_declaration_vat_invoice(self):
        self.ensure_one()
        return {
            'name': _("VAT Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': self.customs_declaration_vat_invoice_id._name,
            'res_id': self.customs_declaration_vat_invoice_id.id,
            'view_mode': 'form',
        }

    def action_show_customs_declaration_customer_invoice(self):
        self.ensure_one()
        return {
            'name': _("Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': self.customs_declaration_customer_invoice_id._name,
            'res_id': self.customs_declaration_customer_invoice_id.id,
            'view_mode': 'form',
        }

