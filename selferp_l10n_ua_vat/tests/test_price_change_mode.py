from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools import float_is_zero, float_compare

from odoo.addons.selferp_contract_settlement.tests.common import AccountContractTestCommon


@tagged('post_install', '-at_install')
class TestPriceChangeMode(AccountContractTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        # create storable product
        cls.product_storable = cls.env['product.product'].create({
            'name': 'product_storable',
            'type': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 1000.0,
        })
        cls.product_storable.categ_id.property_valuation = 'real_time'

        # create and post invoice
        cls.invoice = cls.create_invoice(
            partner=cls.partner_a,
            products=[cls.product_storable],
            amounts=[2],
        )
        cls.post_invoice(cls.invoice)

        accounts = cls.product_storable.product_tmpl_id.get_product_accounts(fiscal_pos=cls.invoice.fiscal_position_id)
        cls.debit_account = accounts['stock_output']
        cls.credit_account = accounts['expense'] or cls.invoice.journal_id.default_account_id

    def test_account_move_reversal_view(self):
        # create wizard record
        wizard = self.env['account.move.reversal'].with_context(
            active_model=self.invoice._name,
            active_ids=self.invoice.ids,
        ).create({
            'journal_id': self.invoice.journal_id.id,
        })

        # check initial state
        self.assertEqual(wizard.refund_method, 'refund')
        self.assertFalse(wizard.price_change_mode)

        # create form
        form = Form(wizard)

        # check initial state
        self.assertEqual(form.refund_method, 'refund')
        self.assertFalse(form.price_change_mode)
        self.assertFalse(form._get_modifier('price_change_mode', 'invisible'))

        # change checkbox
        form.price_change_mode = True
        self.assertTrue(form.price_change_mode)

        # value should be restored and checkbox hidden
        form.refund_method = 'cancel'
        self.assertFalse(form.price_change_mode)
        self.assertTrue(form._get_modifier('price_change_mode', 'invisible'))

        # show it back
        form.refund_method = 'refund'
        self.assertFalse(form.price_change_mode)
        self.assertFalse(form._get_modifier('price_change_mode', 'invisible'))

    def test_credit_note_without_price_change(self):
        # create wizard record with predefined params
        wizard = self.env['account.move.reversal'].with_context(
            active_model=self.invoice._name,
            active_ids=self.invoice.ids,
        ).create({
            'journal_id': self.invoice.journal_id.id,
            'refund_method': 'refund',
            'price_change_mode': False,
        })

        # confirm
        res = wizard.reverse_moves()

        # get created invoice
        credit_note_invoice = self.env['account.move'].browse(res['res_id'])
        self.assertTrue(credit_note_invoice)
        self.assertFalse(credit_note_invoice.price_change_mode)
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

        move_lines_count = len(credit_note_invoice.line_ids)

        # validate invoice
        self.post_invoice(credit_note_invoice)

        # check move lines
        self.assertEqual(len(credit_note_invoice.line_ids), move_lines_count + 2)
        debit_line = credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account)
        self.assertEqual(len(debit_line), 1)
        self.assertTrue(float_is_zero(debit_line.debit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertFalse(float_is_zero(debit_line.credit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertTrue(float_compare(debit_line.credit, 0, precision_rounding=self.invoice.currency_id.rounding) < 0)
        credit_line = credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account)
        self.assertEqual(len(credit_line), 1)
        self.assertTrue(float_is_zero(credit_line.credit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertFalse(float_is_zero(credit_line.debit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertTrue(float_compare(credit_line.debit, 0, precision_rounding=self.invoice.currency_id.rounding) < 0)

    def test_credit_note_with_price_change(self):
        # create wizard record with predefined params
        wizard = self.env['account.move.reversal'].with_context(
            active_model=self.invoice._name,
            active_ids=self.invoice.ids,
        ).create({
            'journal_id': self.invoice.journal_id.id,
            'refund_method': 'refund',
            'price_change_mode': True,
        })

        # confirm
        res = wizard.reverse_moves()

        # get created invoice
        credit_note_invoice = self.env['account.move'].browse(res['res_id'])
        self.assertTrue(credit_note_invoice)
        self.assertTrue(credit_note_invoice.price_change_mode)
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

        move_lines_count = len(credit_note_invoice.line_ids)

        # validate invoice
        self.post_invoice(credit_note_invoice)

        # check move lines count
        self.assertEqual(len(credit_note_invoice.line_ids), move_lines_count)
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not credit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

    def test_debit_note_without_price_change(self):
        # create wizard record with predefined params
        wizard = self.env['account.debit.note'].with_context(
            active_model=self.invoice._name,
            active_ids=self.invoice.ids,
        ).create({
            'journal_id': self.invoice.journal_id.id,
            'copy_lines': True,
            'price_change_mode': False,
        })

        # confirm
        res = wizard.create_debit()

        # get created invoice
        debit_note_invoice = self.env['account.move'].browse(res['res_id'])
        self.assertTrue(debit_note_invoice)
        self.assertFalse(debit_note_invoice.price_change_mode)
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

        move_lines_count = len(debit_note_invoice.line_ids)

        # validate invoice
        self.post_invoice(debit_note_invoice)

        # check move lines
        self.assertEqual(len(debit_note_invoice.line_ids), move_lines_count + 2)
        debit_line = debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account)
        self.assertEqual(len(debit_line), 1)
        self.assertTrue(float_is_zero(debit_line.debit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertFalse(float_is_zero(debit_line.credit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertTrue(float_compare(debit_line.credit, 0, precision_rounding=self.invoice.currency_id.rounding) > 0)
        credit_line = debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account)
        self.assertEqual(len(credit_line), 1)
        self.assertTrue(float_is_zero(credit_line.credit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertFalse(float_is_zero(credit_line.debit, precision_rounding=self.invoice.currency_id.rounding))
        self.assertTrue(float_compare(credit_line.debit, 0, precision_rounding=self.invoice.currency_id.rounding) > 0)

    def test_debit_note_with_price_change(self):
        # create wizard record with predefined params
        wizard = self.env['account.debit.note'].with_context(
            active_model=self.invoice._name,
            active_ids=self.invoice.ids,
        ).create({
            'journal_id': self.invoice.journal_id.id,
            'copy_lines': True,
            'price_change_mode': True,
        })

        # confirm
        res = wizard.create_debit()

        # get created invoice
        debit_note_invoice = self.env['account.move'].browse(res['res_id'])
        self.assertTrue(debit_note_invoice)
        self.assertTrue(debit_note_invoice.price_change_mode)
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

        move_lines_count = len(debit_note_invoice.line_ids)

        # validate invoice
        self.post_invoice(debit_note_invoice)

        # check move lines count
        self.assertEqual(len(debit_note_invoice.line_ids), move_lines_count)
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.debit_account))
        self.assertTrue(not debit_note_invoice.line_ids.filtered(lambda r: r.account_id == self.credit_account))

