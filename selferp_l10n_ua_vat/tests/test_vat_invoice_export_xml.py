import requests

from werkzeug import urls

from odoo.tests import tagged
from odoo.exceptions import UserError

from .common import VATTestCommon


@tagged('-at_install', 'post_install')
class TestVATInvoiceExportXML(VATTestCommon):

    def test_fail_not_vat_invoice(self):
        move = self.create_invoice(
            partner=self.partner_a,
            products=[self.product_a],
            amounts=[1000],
            taxes=[],
        )

        self.assertNotEqual(move.move_type, 'vat_invoice')

        try:
            move.action_vat_export_xml()
            self.fail()
        except UserError as e:
            return
