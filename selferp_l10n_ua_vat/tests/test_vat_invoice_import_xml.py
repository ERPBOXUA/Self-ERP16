from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

from .common import VATTestCommon


IMPORT_FILE_1 = '13010011111111J1201015100000000210420231301.XML'
IMPORT_FILE_2 = 'vendor_vat_invoices.zip'


@tagged('-at_install', 'post_install')
class TestVATInvoiceImportXML(VATTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # set Company 1 as current
        cls.env.user.company_id = cls.company_data['company'].id

        # use Company 2 for import
        cls.import_company = cls.company_data_2['company']

        cls.import_company.vat = '111111111111'

        cls.import_company.vat_journal_id = cls.env['account.journal'].create({
            'company_id': cls.import_company.id,
            'name': "VAT Journal 2",
            'code': 'VAT2',
            'type': 'general',
        })
        cls.import_company.vendor_vat_journal_id = cls.env['account.journal'].create({
            'company_id': cls.import_company.id,
            'name': "Vendor VAT Journal 2",
            'code': 'VVAT2',
            'type': 'general',
        })

        cls.partner_444444446677 = cls.env['res.partner'].create({
            'name': 'ТОВ "Дзвіночок"',
            'vat': '444444446677',
        })

        cls.tax_purchase_20_exclude = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.import_company.id),
                ('type_tax_use', '=', 'purchase'),
                ('price_include', '=', False),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '20'),
            ],
            limit=1,
        )
        cls.tax_purchase_14_exclude = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.import_company.id),
                ('type_tax_use', '=', 'purchase'),
                ('price_include', '=', False),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '14'),
            ],
            limit=1,
        )

    def test_fail_file_not_selected(self):
        try:
            self._wizard().action_confirm()
            self.fail()
        except UserError as e:
            pass

    def test_fail_no_company(self):
        self.import_company.vat = 'none'

        wizard = self._wizard({
            'attachment_ids': [Command.create({
                'name': IMPORT_FILE_1,
                'raw': self._read(IMPORT_FILE_1),
            })],
        })

        try:
            wizard.action_confirm()
            self.fail()
        except UserError as e:
            pass

    def test_fail_no_partner(self):
        self.partner_444444446677.vat = 'none'

        wizard = self._wizard({
            'attachment_ids': [Command.create({
                'name': IMPORT_FILE_1,
                'raw': self._read(IMPORT_FILE_1),
            })],
        })

        try:
            wizard.action_confirm()
            self.fail()
        except UserError as e:
            pass

    def test_single_vendor_vat_invoice(self):
        # do import first
        vendor_vat_invoice = self._do_test_single_vendor_vat_invoice()

        # try to import again
        try:
            self._do_test_single_vendor_vat_invoice()
            self.fail()
        except UserError as e:
            pass

        # change partner and try to import again
        vendor_vat_invoice.partner_id = self.partner_a
        vendor_vat_invoice1 = self._do_test_single_vendor_vat_invoice()

        # try to import again
        try:
            self._do_test_single_vendor_vat_invoice()
            self.fail()
        except UserError as e:
            pass

        # change date and try to import again
        vendor_vat_invoice1.issuance_date = fields.Date.today()
        vendor_vat_invoice2 = self._do_test_single_vendor_vat_invoice()

        # try to import again
        try:
            self._do_test_single_vendor_vat_invoice()
            self.fail()
        except UserError as e:
            pass

        # change external number and try to import again
        vendor_vat_invoice2.external_number = '1111111'
        vendor_vat_invoice3 = self._do_test_single_vendor_vat_invoice()

        # try to import again
        try:
            self._do_test_single_vendor_vat_invoice()
            self.fail()
        except UserError as e:
            pass

    def _do_test_single_vendor_vat_invoice(self):
        wizard = self._wizard({
            'attachment_ids': [
                Command.create({
                    'name': IMPORT_FILE_1,
                    'raw': self._read(IMPORT_FILE_1),
                }),
            ],
        })

        action = wizard.action_confirm()

        self.assertIsNotNone(action)
        self.assertEqual(action.get('view_mode'), 'form')
        self.assertIsNotNone(action.get('res_id'))

        vendor_vat_invoice = self.env['account.move'].browse(action.get('res_id'))

        self._check_single_vendor_vat_invoice(vendor_vat_invoice)

        return vendor_vat_invoice

    def _check_single_vendor_vat_invoice(self, vendor_vat_invoice):
        self.assertTrue(vendor_vat_invoice)
        self.assertEqual(vendor_vat_invoice.move_type, 'vendor_vat_invoice')
        self.assertEqual(vendor_vat_invoice.company_id, self.import_company)
        self.assertEqual(vendor_vat_invoice.partner_id, self.partner_444444446677)
        self.assertEqual(len(vendor_vat_invoice.vat_line_ids), 1)
        self.assertEqual(vendor_vat_invoice.external_number, '28')
        self.assertEqual(vendor_vat_invoice.date, fields.Date.from_string('2023-04-23'))
        self.assertEqual(vendor_vat_invoice.issuance_date, fields.Date.from_string('2023-04-23'))
        self.assertFalse(vendor_vat_invoice.to_vat_invoice_exempt_from_taxation)
        self.assertFalse(vendor_vat_invoice.vat_line_ids[0].product_id)
        self.assertEqual(vendor_vat_invoice.vat_line_ids[0].vat_tax_id, self.tax_purchase_20_exclude)
        self.assertEqual(vendor_vat_invoice.vat_line_ids[0].total_without_vat, 500.00)
        self.assertEqual(vendor_vat_invoice.vat_line_ids[0].vat_amount, 100.00)
        self.assertEqual(vendor_vat_invoice.vat_line_total, 600.00)

    def test_many_vendor_vat_invoice(self):
        wizard = self._wizard({
            'attachment_ids': [
                Command.create({
                    'name': IMPORT_FILE_1,
                    'raw': self._read(IMPORT_FILE_1),
                }),
                Command.create({
                    'name': IMPORT_FILE_2,
                    'raw': self._read(IMPORT_FILE_2),
                }),
            ],
        })

        action = wizard.action_confirm()

        self.assertIsNotNone(action)
        self.assertEqual(action.get('view_mode'), 'tree,form')
        self.assertFalse(action.get('res_id'))
        self.assertIsNotNone(action.get('domain'))
        self.assertEqual(len(action.get('domain')), 1)

        vendor_vat_invoices = self.env['account.move'].search(action.get('domain'))

        self.assertEqual(len(vendor_vat_invoices), 3)

        vendor_vat_invoice_1 = vendor_vat_invoices.filtered(lambda r: r.external_number == '28')
        self._check_single_vendor_vat_invoice(vendor_vat_invoice_1)

        vendor_vat_invoice_2 = vendor_vat_invoices.filtered(lambda r: r.external_number == '29')
        self.assertTrue(vendor_vat_invoice_2)
        self.assertEqual(vendor_vat_invoice_2.move_type, 'vendor_vat_invoice')
        self.assertEqual(vendor_vat_invoice_2.company_id, self.import_company)
        self.assertEqual(vendor_vat_invoice_2.partner_id, self.partner_444444446677)
        self.assertEqual(len(vendor_vat_invoice_2.vat_line_ids), 1)
        self.assertEqual(vendor_vat_invoice_2.external_number, '29')
        self.assertEqual(vendor_vat_invoice_2.date, fields.Date.from_string('2023-04-24'))
        self.assertEqual(vendor_vat_invoice_2.issuance_date, fields.Date.from_string('2023-04-24'))
        self.assertFalse(vendor_vat_invoice_2.to_vat_invoice_exempt_from_taxation)
        self.assertFalse(vendor_vat_invoice_2.vat_line_ids[0].product_id)
        self.assertEqual(vendor_vat_invoice_2.vat_line_ids[0].vat_tax_id, self.tax_purchase_20_exclude)
        self.assertEqual(vendor_vat_invoice_2.vat_line_ids[0].total_without_vat, 200.00)

        vendor_vat_invoice_3 = vendor_vat_invoices.filtered(lambda r: r.external_number == '30')
        self.assertTrue(vendor_vat_invoice_3)
        self.assertEqual(vendor_vat_invoice_3.move_type, 'vendor_vat_invoice')
        self.assertEqual(vendor_vat_invoice_3.company_id, self.import_company)
        self.assertEqual(vendor_vat_invoice_3.partner_id, self.partner_444444446677)
        self.assertEqual(len(vendor_vat_invoice_3.vat_line_ids), 2)
        self.assertEqual(vendor_vat_invoice_3.external_number, '30')
        self.assertEqual(vendor_vat_invoice_3.date, fields.Date.from_string('2023-04-25'))
        self.assertEqual(vendor_vat_invoice_3.issuance_date, fields.Date.from_string('2023-04-25'))
        self.assertFalse(vendor_vat_invoice_3.to_vat_invoice_exempt_from_taxation)
        self.assertFalse(vendor_vat_invoice_3.vat_line_ids[0].product_id)
        self.assertEqual(vendor_vat_invoice_3.vat_line_ids[0].vat_tax_id, self.tax_purchase_20_exclude)
        self.assertEqual(vendor_vat_invoice_3.vat_line_ids[0].total_without_vat, 350.00)
        self.assertFalse(vendor_vat_invoice_3.vat_line_ids[1].product_id)
        self.assertEqual(vendor_vat_invoice_3.vat_line_ids[1].vat_tax_id, self.tax_purchase_14_exclude)
        self.assertEqual(vendor_vat_invoice_3.vat_line_ids[1].total_without_vat, 100.00)

    @classmethod
    def _wizard(cls, values={}):
        return cls.env['account.move.vat_invoice.import'].create(values)

    @classmethod
    def _read(cls, file_name):
        with file_open(f'selferp_l10n_ua_vat/tests/testfiles/{file_name}', 'br') as fd:
            return fd.read()
