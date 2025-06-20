from datetime import timedelta

from odoo import fields, Command
from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_vat.tests.common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVATExport(VATTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_vat_export(self):
        customer_invoice = self.create_invoice(
            partner=self.partner_a,
            products=[self.product_a],
            amounts=[1000],
            taxes=[self.tax_sale_0],
            currency=self.currency_data['currency'],
        )
        customer_invoice.write({
            'is_customs_declaration': True,
            'cd_date': fields.Date.today() - timedelta(days=1),
            'cd_currency_rate': 40,
        })
        self.post_invoice(customer_invoice)

        self.assertEqual(customer_invoice.amount_untaxed, 1000)
        self.assertEqual(customer_invoice.amount_tax, 0)
        self.assertEqual(customer_invoice.amount_total, 1000)

        action = customer_invoice.action_create_customs_declaration_vat_invoice()
        self.assertTrue(action)

        vat_invoice = customer_invoice.customs_declaration_vat_invoice_id

        self.assertTrue(vat_invoice)
        self.assertEqual(action['res_model'], vat_invoice._name)
        self.assertEqual(action['res_id'], vat_invoice.id)
        self.assertEqual(vat_invoice.move_type, 'vat_invoice')
        self.assertEqual(vat_invoice.state, 'draft')
        self.assertEqual(vat_invoice.customs_declaration_customer_invoice_id, customer_invoice)
        self.assertEqual(vat_invoice.partner_id, customer_invoice.partner_id)
        self.assertEqual(vat_invoice.date, customer_invoice.cd_date)
        self.assertTrue(vat_invoice.not_issued_to_customer)
        self.assertEqual(vat_invoice.reason_type, '07')
        self.assertEqual(len(vat_invoice.vat_line_ids), 1)
        self.assertEqual(vat_invoice.vat_line_ids.product_id, self.product_a)
        self.assertEqual(vat_invoice.vat_line_ids.quantity, 1)
        self.assertEqual(vat_invoice.vat_line_ids.price_unit, 40000)
        self.assertEqual(vat_invoice.vat_line_ids.total, 40000)
        self.assertEqual(vat_invoice.vat_line_ids.vat_tax_id, self.tax_sale_0)
        self.assertEqual(len(vat_invoice.line_ids), 2)
        self.assertEqual(vat_invoice.line_ids[0].debit, 0)
        self.assertEqual(vat_invoice.line_ids[0].credit, 0)
        self.assertEqual(vat_invoice.line_ids[1].debit, 0)
        self.assertEqual(vat_invoice.line_ids[1].credit, 0)
        self.assertEqual(vat_invoice.vat_line_subtotal, 40000)
        self.assertEqual(vat_invoice.vat_line_tax, 0)
        self.assertEqual(vat_invoice.vat_line_total, 40000)

