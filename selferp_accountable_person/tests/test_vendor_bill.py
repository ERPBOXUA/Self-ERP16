import datetime

from odoo import fields, api, Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_is_zero

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install')
class TestVendorBill(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.env.ref('base.main_company')

        user = cls.env['res.users'].create({
            'name': 'Self-ERP accountman!',
            'login': 'accounting',
            'password': 'accounting',
            'company_id': company.id,
            'company_ids': company.ids,
            'groups_id': [
                (6, 0, cls.env.user.groups_id.ids),
                (4, cls.env.ref('account.group_account_manager').id),
                (4, cls.env.ref('account.group_account_user').id),
            ],
        })
        user.partner_id.email = 'accounting@self-erp.com'

        cls.env = api.Environment(cls.env.cr, user.id, {})

        cls.accountable_account = cls.env['account.account'].search([
            ('code', '=', '372100'),
            ('company_id', '=', cls.env.company.id),
        ])
        cls.accountable_account.account_type = 'liability_payable'

        # This contact has corresponding employee
        cls.existing_vendor = cls.env.ref('hr.work_contact_fpi')

    def test_case_1(self):
        # 1. The user opens the contact card and enters the account for mutual settlements with accountable persons
        # in the field "Settlements with accountable persons"
        self.existing_vendor.property_account_accountable_id = self.accountable_account

        # 2. The user opens the Purchase Order and activates the "Advance report" option.
        purchase_order = self.env['purchase.order'].search([
            ('partner_id', '!=', self.existing_vendor.id),
            ('state', 'in', ('draft', 'sent')),
        ], limit=1)
        purchase_order.is_advance_report = True

        # 3. The user fills in the Vendor field from the list of Company employees
        purchase_order.partner_id = self.existing_vendor

        # 4. User confirms the purchase order
        purchase_order.button_confirm()

        # 5. The user confirms the delivery of the products
        purchase_order.picking_ids.action_set_quantities_to_reservation()
        purchase_order.picking_ids.button_validate()

        # 6. The user creates an invoice from the Purchase order
        invoice_action = purchase_order.action_create_invoice()

        # 7. The "Advance report" option is automatically added to the invoice generated from the purchase order.
        invoice = self.env['account.move'].search([('id', '=', invoice_action['res_id'])])
        self.assertTrue(invoice.is_advance_report, "Advance Report should be set!")

        # 8. User confirms invoice. Journal entry with appropriate account is created
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        accountable_line = invoice.line_ids.filtered(
            lambda r: not float_is_zero(r.credit, precision_rounding=r.currency_id.rounding)
        )
        self.assertEqual(
            len(accountable_line),
            1,
            "Should be one line for mutual settlements with accountable persons",
        )
        self.assertEqual(
            accountable_line.account_id,
            self.accountable_account,
            "Invalid account in line for mutual settlements with accountable persons",
        )

        # 9. The invoice is displayed in a separate menu item Accounting > Vendors > Advance reports

    def test_convert_error_fix(self):
        self.existing_vendor.property_account_accountable_id = self.accountable_account

        product = self.env.ref('product.expense_hotel')

        invoice = self.env['account.move'].create({
            'partner_id': self.existing_vendor.id,
            'move_type': 'in_invoice',
            'invoice_date': datetime.date.today(),
            'date': datetime.date.today(),
            'invoice_line_ids': [Command.create({'name': product.name, 'product_id': product.id, 'price_unit': product.list_price})],
        })

        accountable_line = invoice.line_ids.filtered(
            lambda r: not float_is_zero(r.credit, precision_rounding=r.currency_id.rounding) and r.account_id == self.accountable_account
        )
        self.assertEqual(
            len(accountable_line),
            0,
            "Should not be any lines for mutual settlements with accountable persons"
        )

        invoice.action_convert_to_advance_report()

        accountable_line = invoice.line_ids.filtered(
            lambda r: not float_is_zero(r.credit, precision_rounding=r.currency_id.rounding) and r.account_id == self.accountable_account
        )
        self.assertEqual(
            len(accountable_line),
            1,
            "Should be one line for mutual settlements with accountable persons",
        )
        self.assertEqual(
            accountable_line.account_id,
            self.accountable_account,
            "Invalid account in line for mutual settlements with accountable persons",
        )

        invoice.action_convert_to_vendor_bill()

        accountable_line = invoice.line_ids.filtered(
            lambda r: not float_is_zero(r.credit, precision_rounding=r.currency_id.rounding) and r.account_id == self.accountable_account
        )
        self.assertEqual(
            len(accountable_line),
            0,
            "Should not be any lines for mutual settlements with accountable persons",
        )

    def test_empty_move_account(self):
        self.existing_vendor.property_account_accountable_id = self.accountable_account
        # TODO: ask Anton then fix or remove (this test is useless since there are no lines in the invoice)

        # invoice = self.env['account.move'].create({
        #     'is_advance_report': True,
        #     'partner_id': self.existing_vendor.id,
        #     'move_type': 'in_invoice',
        #     'invoice_date': datetime.date.today(),
        #     'date': datetime.date.today(),
        # })
        #
        # accountable_line = invoice.line_ids.filtered(lambda r: r.account_id == self.accountable_account)
        #
        # self.assertEqual(
        #     len(accountable_line),
        #     1,
        #     "Should be one line for mutual settlements with accountable persons",
        # )
        # self.assertEqual(
        #     accountable_line.account_id,
        #     self.accountable_account,
        #     "Invalid account in line for mutual settlements with accountable persons",
        # )
