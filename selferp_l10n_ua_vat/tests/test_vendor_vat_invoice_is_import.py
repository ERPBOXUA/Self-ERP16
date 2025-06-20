from odoo import Command
from odoo.tests import Form, tagged

from .common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVendorVATInvoiceIsImport(VATTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.settlements_with_customs_account_id = cls.env['account.account'].search(
            [
                ('company_id', '=', cls.env.user.company_id.id),
                ('code', '=', '377100'),
            ],
            limit=1,
        )

    def test_non_import(self):
        vat_invoice = self._create_vendor_vat_invoice()

        self.assertEqual(len(vat_invoice.line_ids), 2)
        for line in vat_invoice.line_ids:
            if line.account_id != vat_invoice.company_id.vat_account_id:
                self.assertEqual(line.account_id, vat_invoice.company_id.vat_account_unconfirmed_credit_id)

    def test_import_form(self):
        vat_invoice = self._create_vendor_vat_invoice()
        self.assertFalse(vat_invoice.is_import)
        self.assertFalse(vat_invoice.settlements_with_customs_account_id)

        form = Form(vat_invoice)

        self.assertFalse(form.is_import)
        self.assertFalse(vat_invoice.settlements_with_customs_account_id)
        self.assertTrue(form._get_modifier('settlements_with_customs_account_id', 'invisible'))
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'required'))

        form.is_import = True
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'invisible'))
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'readonly'))
        self.assertTrue(form._get_modifier('settlements_with_customs_account_id', 'required'))
        self.assertEqual(form.settlements_with_customs_account_id, self.settlements_with_customs_account_id)

        form.is_import = False
        self.assertFalse(vat_invoice.settlements_with_customs_account_id)
        self.assertTrue(form._get_modifier('settlements_with_customs_account_id', 'invisible'))
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'required'))

        form.is_import = True
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'invisible'))
        self.assertFalse(form._get_modifier('settlements_with_customs_account_id', 'readonly'))
        self.assertTrue(form._get_modifier('settlements_with_customs_account_id', 'required'))
        self.assertEqual(form.settlements_with_customs_account_id, self.settlements_with_customs_account_id)

    def test_import_1(self):
        vat_invoice = self._create_vendor_vat_invoice({
            'is_import': True,
            'settlements_with_customs_account_id': self.settlements_with_customs_account_id.id,
        })

        self.assertEqual(len(vat_invoice.line_ids), 2)
        for line in vat_invoice.line_ids:
            if line.account_id != vat_invoice.company_id.vat_account_id:
                self.assertEqual(line.account_id, self.settlements_with_customs_account_id)

    def test_import_2(self):
        vat_invoice = self._create_vendor_vat_invoice({
            'is_import': True,
            'settlements_with_customs_account_id': self.env.user.company_id.vat_account_confirmed_credit_id.id,
        })

        self.assertEqual(len(vat_invoice.line_ids), 2)

        for line in vat_invoice.line_ids:
            if line.account_id != vat_invoice.company_id.vat_account_id:
                self.assertEqual(line.account_id, vat_invoice.company_id.vat_account_confirmed_credit_id)

    def _create_vendor_vat_invoice(self, extra_values=None):
        values = {
            'move_type': 'vendor_vat_invoice',
            'partner_id': self.partner_a.id,
            'vat_line_ids': [Command.create({
                'total_without_vat': 1000,
                'vat_tax_id': self.tax_sale_20.id,
            })],
        }
        if extra_values:
            values.update(extra_values)
        return self.env['account.move'].create(values)

