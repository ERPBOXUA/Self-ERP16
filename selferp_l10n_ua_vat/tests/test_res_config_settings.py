from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestResConfigSettings(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref='l10n_ua.l10n_ua_psbo_chart_template')

        (
            cls.default_vat_account,
            cls.default_vat_account_unconfirmed,
            cls.default_vat_account_confirmed,
            cls.default_vat_account_unconfirmed_credit,
            cls.default_vat_account_confirmed_credit,
        ) = cls.env.company.get_vat_default_accounts()

        (
            cls.default_vat_default_tax,
            cls.default_vat_default_tax_credit,
        ) = cls.env.company.get_vat_default_taxes()

    def test_is_vat_onchange(self):
        """
        Test various scenarios of behavior on change settings value via a form
        """
        form = Form(self.env['res.config.settings'].create({}))

        # check default values
        self.assertEqual(form.vat_payer, False)
        self.assertTrue(not form.vat_account_id)
        self.assertTrue(not form.vat_account_unconfirmed_id)
        self.assertTrue(not form.vat_account_confirmed_id)
        self.assertTrue(not form.vat_account_unconfirmed_credit_id)
        self.assertTrue(not form.vat_account_confirmed_credit_id)
        self.assertTrue(not form.vat_journal_id)
        self.assertTrue(not form.vendor_vat_journal_id)
        self.assertTrue(not form.first_event_journal_id)
        self.assertTrue(not form.vat_default_tax_id)
        self.assertTrue(not form.vat_default_tax_credit_id)
        self.assertTrue(not form.vat_default_product_id)

        self.assertEqual(form.vat_reg_terms_1, 31)
        self.assertEqual(form.vat_reg_terms_1_next_month, False)
        self.assertEqual(form.vat_reg_terms_2, 15)
        self.assertEqual(form.vat_reg_terms_2_next_month, True)

        # switch on option
        form.vat_payer = True

        self.assertEqual(form.vat_payer, True)
        self.assertEqual(form.vat_account_id, self.default_vat_account)
        self.assertEqual(form.vat_account_unconfirmed_id, self.default_vat_account_unconfirmed)
        self.assertEqual(form.vat_account_confirmed_id, self.default_vat_account_confirmed)
        self.assertEqual(form.vat_account_unconfirmed_credit_id, self.default_vat_account_unconfirmed_credit)
        self.assertEqual(form.vat_account_confirmed_credit_id, self.default_vat_account_confirmed_credit)
        self.assertTrue(form.vat_journal_id)
        self.assertTrue(form.vendor_vat_journal_id)
        self.assertTrue(form.first_event_journal_id)
        self.assertEqual(form.vat_default_tax_id, self.default_vat_default_tax)
        self.assertEqual(form.vat_default_tax_credit_id, self.default_vat_default_tax_credit)
        self.assertTrue(form.vat_default_product_id)

        self.assertEqual(form.vat_reg_terms_1, 31)
        self.assertEqual(form.vat_reg_terms_1_next_month, False)
        self.assertEqual(form.vat_reg_terms_2, 15)
        self.assertEqual(form.vat_reg_terms_2_next_month, True)

        test_journals = self.env['account.journal'].search([], limit=3)
        test_product = self.env['product.product'].search([], limit=1)

        form.vat_journal_id = test_journals[0]
        form.vendor_vat_journal_id = test_journals[1]
        form.first_event_journal_id = test_journals[2]
        form.vat_default_product_id = test_product
        form.save()

        # check values
        self.assertEqual(form.vat_payer, True)
        self.assertEqual(form.vat_account_id, self.default_vat_account)
        self.assertEqual(form.vat_account_unconfirmed_id, self.default_vat_account_unconfirmed)
        self.assertEqual(form.vat_account_confirmed_id, self.default_vat_account_confirmed)
        self.assertEqual(form.vat_account_unconfirmed_credit_id, self.default_vat_account_unconfirmed_credit)
        self.assertEqual(form.vat_account_confirmed_credit_id, self.default_vat_account_confirmed_credit)
        self.assertEqual(form.vat_journal_id, test_journals[0])
        self.assertEqual(form.vendor_vat_journal_id, test_journals[1])
        self.assertEqual(form.first_event_journal_id, test_journals[2])
        self.assertEqual(form.vat_default_tax_id, self.default_vat_default_tax)
        self.assertEqual(form.vat_default_tax_credit_id, self.default_vat_default_tax_credit)
        self.assertEqual(form.vat_default_product_id, test_product)

        # check reg terms (possible values from 1 to 31)
        for day in range(-64, 64):
            form.vat_reg_terms_1 = day
            if day < 1 or day > 31:
                with self.assertRaises(ValidationError):
                    form.save()
            else:
                form.save()
        form.vat_reg_terms_1 = 31

        for day in range(-64, 64):
            form.vat_reg_terms_2 = day
            if day < 1 or day > 31:
                with self.assertRaises(ValidationError):
                    form.save()
            else:
                form.save()
        form.vat_reg_terms_2 = 15
