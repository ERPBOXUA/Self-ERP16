from datetime import timedelta

from odoo import fields, Command
from odoo.tests import tagged

from .common import AccountTestCommon


@tagged('-at_install', 'post_install')
class TestStockPickingAccountingDate(AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        # get price from move for SVL
        cls.env.ref('product.product_category_all').write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        cls.product_1 = cls.env['product.product'].create({
            'type': 'product',
            'name': 'Холодильник',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 22000.0,
            'standard_price': 20000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
        })

    def test_default_behavior(self):
        self._test_dates()

    def test_accounting_date_past(self):
        self._test_dates(fields.Datetime.now() - timedelta(days=3))

    def test_accounting_date_future(self):
        self._test_dates(fields.Datetime.now() + timedelta(days=3))

    def _test_dates(self, accounting_date=None):
        today = fields.Date.today()

        # create purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': today,
            'order_line': [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })

        # confirm purchase order
        purchase_order.button_confirm()

        if accounting_date:
            purchase_order.picking_ids.write({
                'accounting_date': accounting_date,
            })

        self.receive_purchase_order_full(purchase_order)

        # determine check date
        check_date = accounting_date and accounting_date.date() or fields.Date.today()

        # check dates
        stock_picking = purchase_order.picking_ids
        self.assertEqual(stock_picking.date.date(), today)

        self.assertEqual(1, len(stock_picking.move_ids))
        self.assertEqual(stock_picking.move_ids.date.date(), check_date)

        self.assertEqual(1, len(stock_picking.move_ids.move_line_ids))
        self.assertEqual(stock_picking.move_ids.move_line_ids.date.date(), check_date)

        self.assertEqual(1, len(stock_picking.move_ids.stock_valuation_layer_ids))
        self.assertEqual(stock_picking.move_ids.stock_valuation_layer_ids.account_move_id.date, check_date)
        self.assertEqual(stock_picking.move_ids.stock_valuation_layer_ids.account_move_id.line_ids[0].date, check_date)
        self.assertEqual(stock_picking.move_ids.stock_valuation_layer_ids.account_move_id.line_ids[1].date, check_date)
