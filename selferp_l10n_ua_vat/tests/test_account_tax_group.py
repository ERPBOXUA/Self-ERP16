from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountTaxGroup(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_is_vat_onchange(self):
        """
        Test various scenarios of behavior on change is_vat field value via a form
        """
        form = Form(self.env['account.tax.group'])

        # default values not set
        self.assertEqual(form.is_vat, False)
        self.assertEqual(form.vat_code, False)

        # set value - code is empty
        form.is_vat = True
        self.assertEqual(form.is_vat, True)
        self.assertEqual(form.vat_code, False)

        # fill code
        form.vat_code = '123'
        self.assertEqual(form.is_vat, True)
        self.assertEqual(form.vat_code, '123')

        # clear is_vat - code should be cleared also
        form.is_vat = False
        self.assertEqual(form.is_vat, False)
        self.assertEqual(form.vat_code, False)

        # set value back - code is empty
        form.is_vat = True
        self.assertEqual(form.is_vat, True)
        self.assertEqual(form.vat_code, False)
