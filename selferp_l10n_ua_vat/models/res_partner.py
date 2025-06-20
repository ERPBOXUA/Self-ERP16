from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tracking_first_event = fields.Selection(
        selection=[
            ('in_general', "In general by counterparty"),
            ('by_contract', "In terms of contracts"),
            ('by_order', "In terms of orders"),
        ],
        string="Tracking the First Event for Customer",
        default='by_contract',
        required=True,
        index=True,
        help="Select the option to track the first VAT event for customers (VAT liabilities)",
    )

    tracking_first_event_vendor = fields.Selection(
        selection=[
            ('in_general', "In general by counterparty"),
            ('by_contract', "In terms of contracts"),
            ('by_order', "In terms of orders"),
        ],
        string="Tracking the First Event for Vendor",
        default='by_contract',
        required=True,
        index=True,
        help="Select the option to track the first VAT event for suppliers (VAT credit)",
    )

    vat_invoice_total = fields.Monetary(
        string="Total VAT Invoice",
        compute='_compute_vat_invoice_total',
    )
    vendor_vat_invoice_total = fields.Monetary(
        string="Total Vendor VAT Invoice",
        compute='_compute_vendor_vat_invoice_total',
    )
    vat_non_payer = fields.Boolean(
        string="VAT Non-payer",
        default=False,
        help="Check the box if the partner is non Ukrainian VAT payer. The TAX ID will be automatically fill in with the value 100000000000 for VAT invoices/adjustments.",
    )

    def _compute_vat_invoice_total(self):
        for rec in self:
            rec.vat_invoice_total = sum(
                self.env['account.move']
                    .search(
                        domain=[
                            ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
                            ('partner_id', '=', rec.id),
                        ],
                    )
                    .mapped('vat_line_total')
            )

    def _compute_vendor_vat_invoice_total(self):
        for rec in self:
            rec.vendor_vat_invoice_total = sum(
                self.env['account.move']
                    .search(
                        domain=[
                            ('move_type', 'in', ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')),
                            ('partner_id', '=', rec.id),
                        ],
                    )
                    .mapped('vat_line_total')
            )

    def action_view_vat_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("VAT Invoices"),
            'res_model': 'account.move',
            'domain': [
                ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
                ('partner_id', '=', self.id),
            ],
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('selferp_l10n_ua_vat.account_move_view_tree_vat_invoice').id, 'tree'),
                (False, 'form'),
            ],
            'search_view_id': [self.env.ref('selferp_l10n_ua_vat.account_move_view_search_vat_invoice').id, 'search'],
        }

    def action_view_vendor_vat_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Vendor VAT Invoices"),
            'res_model': 'account.move',
            'domain': [
                ('move_type', 'in', ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')),
                ('partner_id', '=', self.id),
            ],
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('selferp_l10n_ua_vat.account_move_view_tree_vat_invoice').id, 'tree'),
                (False, 'form'),
            ],
        }
