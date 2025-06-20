from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestResConfigSettings(TestPoSCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        chart_template_ref = chart_template_ref or 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

        # fix _onchange_tax_exigibility issue in res.config.settings
        if cls.env['account.tax'].search_count([
            ('company_id', '=', cls.env.company.id),
            ('tax_exigibility', '=', 'on_payment'),
        ]):
            cls.env.company.tax_exigibility = True

    def test_set_vat_partner_id(self):
        form = Form(self.env['res.config.settings'])
        form.pos_vat_partner_id = self.customer
        form.save()
        self.assertEqual(self.basic_config.vat_partner_id, form.pos_vat_partner_id)
