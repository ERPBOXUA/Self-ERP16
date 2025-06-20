from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_vat.tests.common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVATAdjustmentInvoiceSequence(VATTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.seq_account_move_vat_adjustment_invoice = cls.env.ref(
            'selferp_l10n_ua_vat.seq_account_move_vat_adjustment_invoice',
            raise_if_not_found=False,
        )

    def test_seq_account_move_vat_adjustment_invoice(self):
        self.assertTrue(self.seq_account_move_vat_adjustment_invoice)

    def test_companies_sequence_vat_adjustment_invoice(self):
        companies = self.env['res.company'].search_count([('sequence_vat_adjustment_invoice_id', '=', False)])
        self.assertFalse(companies)

    def not_test_create_unlink_company(self):
        company = self.env['res.company'].create({
            'name': "HO company",
        })
        self.assertTrue(company.sequence_vat_adjustment_invoice_id)
        self.assertEqual(company, company.sequence_vat_adjustment_invoice_id.company_id)
        company_sequence_vat_adjustment_invoice_id = company.sequence_vat_adjustment_invoice_id.id
        self.assertNotEqual(self.seq_account_move_vat_adjustment_invoice, company.sequence_vat_adjustment_invoice_id)
        company.unlink()

        is_unlink_company_sequence_vat_adjustment_invoice = self.env['ir.sequence'].search_count(
            [('id', '=', company_sequence_vat_adjustment_invoice_id)],
        )
        self.assertFalse(is_unlink_company_sequence_vat_adjustment_invoice)
