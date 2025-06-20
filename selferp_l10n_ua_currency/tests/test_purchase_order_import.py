import itertools

from datetime import date, timedelta

from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools import float_round

from odoo.addons.selferp_l10n_ua_ext.tests.common import AccountTestCommon


@tagged('post_install', '-at_install')
class TestPurchaseOrderImport(AccountTestCommon):

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
        cls.product_2 = cls.env['product.product'].create({
            'type': 'product',
            'name': 'Пральна машина',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 12000.0,
            'standard_price': 11000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
        })
        cls.product_3 = cls.env['product.product'].create({
            'type': 'product',
            'name': 'Лінолеум',
            'uom_id': cls.env.ref('uom.product_uom_meter').id,
            'uom_po_id': cls.env.ref('uom.product_uom_meter').id,
            'lst_price': 17.73,
            'standard_price': 17.73,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
        })

        cls.product_consu_1 = cls.env['product.product'].create({
            'type': 'consu',
            'name': 'consu 1',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 100.0,
            'standard_price': 100.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.product_consu_2 = cls.env['product.product'].create({
            'type': 'consu',
            'name': 'consu 2',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 200.0,
            'standard_price': 200.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })

        cls.product_service_1 = cls.env['product.product'].create({
            'type': 'service',
            'purchase_method': 'purchase',
            'name': 'service 1',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 300.0,
            'standard_price': 300.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.product_service_2 = cls.env['product.product'].create({
            'type': 'service',
            'purchase_method': 'purchase',
            'name': 'service 2',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 400.0,
            'standard_price': 400.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })

        cls.product_landed_cost = cls.env['product.product'].create({
            'type': 'service',
            'name': 'product_landed_cost',
            'landed_cost_ok': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })

        cls.currency_usd = cls.env.ref('base.USD')

        cls.currency_rates = cls.env['res.currency.rate'].create([
            {
                'company_id': cls.env.company.id,
                'name': date(2024, 1, 19),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 38.0,
            },
            {
                'company_id': cls.env.company.id,
                'name': fields.Date.today(),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 36.5,
            },
        ])

        cls.customs_declaration_date = fields.Date.today() - timedelta(days=3)

    def test_create_landed_cost(self):
        # create purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': fields.Date.today(),
            'currency_id': self.currency_usd.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],

            'is_import': True,
        })

        # confirm purchase order
        purchase_order.button_confirm()
        stock_picking = purchase_order.picking_ids
        self.assertEqual(len(stock_picking), 1)

        # write customs declaration info
        stock_picking.write({
            'customs_declaration_date': self.customs_declaration_date,
            'customs_declaration_line_ids': [
                Command.create({
                    'product_id': self.product_landed_cost.id,
                    'description': '1234',
                    'amount': 123,
                }),
                Command.create({
                    'product_id': self.product_landed_cost.id,
                    'description': '4321',
                    'amount': 321,
                }),
            ],
        })

        # receive purchase order
        self.receive_purchase_order_full(purchase_order)

        # create and check landed cost
        landed_cost_action = stock_picking.action_create_landed_cost()
        self.assertFalse(not landed_cost_action)

        landed_cost = self.env[landed_cost_action['res_model']].browse(landed_cost_action['res_id'])
        self.assertFalse(not landed_cost)
        self.assertEqual(landed_cost.state, 'draft')
        self.assertEqual(landed_cost.date, stock_picking.customs_declaration_date)
        self.assertEqual(landed_cost.target_model, 'picking')
        self.assertEqual(1, len(landed_cost.picking_ids))
        self.assertEqual(landed_cost.picking_ids, stock_picking)
        self.assertEqual(2, len(landed_cost.cost_lines))
        self.assertRecordValues(landed_cost.cost_lines, [
            {
                'name': stock_picking.customs_declaration_line_ids[0].description,
                'product_id': stock_picking.customs_declaration_line_ids[0].product_id.id,
                'price_unit': stock_picking.customs_declaration_line_ids[0].amount,
            },
            {
                'name': stock_picking.customs_declaration_line_ids[1].description,
                'product_id': stock_picking.customs_declaration_line_ids[1].product_id.id,
                'price_unit': stock_picking.customs_declaration_line_ids[1].amount,
            },
        ])

    def test_validation_non_import(self):
        # create purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': fields.Date.today(),
            'currency_id': self.currency_usd.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })

        # confirm purchase order
        self.confirm_and_receive_purchase_order(purchase_order)

        # check SVL
        stock_picking = purchase_order.picking_ids

        self.assertEqual(1, len(stock_picking.move_ids))
        self.assertEqual(1, len(stock_picking.move_ids.stock_valuation_layer_ids))

        stock_valuation_layer = stock_picking.move_ids.stock_valuation_layer_ids

        self.assertEqual(
            stock_valuation_layer.value,
            float_round(
                purchase_order.amount_untaxed/self.currency_rates[-1].rate,
                precision_rounding=self.env.company.currency_id.rounding,
            ),
        )

        # create and check vendor bill
        action = purchase_order.action_create_invoice()
        vendor_bill = self.env[action['res_model']].browse(action['res_id'])
        self.assertEqual(1, len(vendor_bill.invoice_line_ids))
        self.assertRecordValues(
            vendor_bill.invoice_line_ids,
            [
                {
                    'product_id': purchase_order.order_line[0].product_id.id,
                    'quantity': purchase_order.order_line[0].product_qty,
                    'price_unit': purchase_order.order_line[0].price_unit,
                    'debit': stock_valuation_layer.value,
                    'credit': 0,
                }
            ]
        )

    def test_unbalanced_move_lines_on_different_currency_rates(self):
        """ Account move contains lines with products and last line which
            balance other records.

            But on creating a vendor bill from import PO, currency rate for
            move lines with product should be computed by import rate
            or advances info, while currency rate for balancing line
            computed by move date since it has no linkage with
            stock move or import purchase order.

        :return:
        """
        # create and validate purchase order
        purchase_order, stock_picking = self._create_import_purchase_order(
            [],
            [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 5,
                    'price_unit': 500,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 10,
                    'price_unit': 430,
                }),
            ],
        )

        # use different import currency rate as in the system
        stock_picking.write({
            'customs_declaration_date': self.customs_declaration_date,
            'customs_declaration_currency_rate': 38.5,
        })

        # validate and check picking
        self._validate_and_check_stock_picking(
            purchase_order,
            stock_picking,
            None,
            [],
            [],
            skip_post_bill=True,
        )

        # create and check vendor bill
        # get a vendor bill
        vendor_bill = stock_picking.vendor_bill_id.sudo()

        self.assertEqual(vendor_bill.state, 'draft')
        self.assertEqual(len(vendor_bill.line_ids), 3)                                  # 2 products + 1 balance line
        self.assertEqual(vendor_bill.invoice_date, stock_picking.customs_declaration_date)     # invoice date comes from import date
        self.assertEqual(vendor_bill.line_ids[0].currency_rate, vendor_bill.line_ids[1].currency_rate)
        self.assertEqual(vendor_bill.line_ids[1].currency_rate, vendor_bill.line_ids[2].currency_rate)
        self.assertEqual(vendor_bill.line_ids[0].currency_rate, 1 / stock_picking.customs_declaration_currency_rate)
        self.assertEqual(abs(vendor_bill.line_ids[0].balance + vendor_bill.line_ids[1].balance), abs(vendor_bill.line_ids[2].balance))

        invoice_date = date(2024, 1, 19)

        # change date (use another currency rate for balance line)
        with Form(vendor_bill) as form:
            form.invoice_date = invoice_date

        self.assertEqual(vendor_bill.invoice_date, invoice_date)
        self.assertNotEqual(vendor_bill.invoice_date, stock_picking.customs_declaration_date)
        self.assertEqual(vendor_bill.line_ids[0].currency_rate, vendor_bill.line_ids[1].currency_rate)
        self.assertEqual(vendor_bill.line_ids[1].currency_rate, vendor_bill.line_ids[2].currency_rate)
        self.assertEqual(vendor_bill.line_ids[0].currency_rate, 1 / stock_picking.customs_declaration_currency_rate)
        self.assertEqual(abs(vendor_bill.line_ids[0].balance + vendor_bill.line_ids[1].balance), abs(vendor_bill.line_ids[2].balance))

    def test_import_case_01(self):
        """ Case 1, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            with single advance on whole amount
        """
        self._test_import(
            [
                {
                    'amount': 6800.0,
                    'currency_rate': 38.0,
                    'reconciled': True,
                },
            ],
            [
                {
                    'unit_cost': 19000.0,
                    'value': 95000.0,
                },
                {
                    'unit_cost': 16340.0,
                    'value': 163400.0,
                },
            ],
        )

    def test_import_case_02(self):
        """ Case 2, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            with a single advance on partial amount
        """
        self._test_import(
            [
                {
                    'amount': 3000.0,
                    'currency_rate': 38.0,
                    'reconciled': True,
                },
            ],
            [
                {
                    'unit_cost': 19139.71,
                    'product_uom_qty': 5,
                    'quantity': 4,
                    'value': 76558.84,
                },
                {
                    'unit_cost': 16460.15,
                    'product_uom_qty': 10,
                    'quantity': 9,
                    'value': 148141.35,
                },
                {
                    'unit_cost': 19139.69,
                    'quantity': 1,
                    'value': 19139.69,
                },
                {
                    'unit_cost': 16460.12,
                    'quantity': 1,
                    'value': 16460.12,
                },
            ],
        )

    def test_import_case_03(self):
        """ Case 3, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            with two advances on the whole amount
        """
        self._test_import(
            [
                {
                    'amount': 3000.0,
                    'currency_rate': 38.0,
                    'reconciled': True,
                },
                {
                    'amount': 3800.0,
                    'currency_rate': 39.0,
                    'reconciled': True,
                },
            ],
            [
                {
                    'unit_cost': 19279.41,
                    'product_uom_qty': 5,
                    'quantity': 4,
                    'value': 77117.64,
                },
                {
                    'unit_cost': 16580.29,
                    'product_uom_qty': 10,
                    'quantity': 9,
                    'value': 149222.61,
                },
                {
                    'unit_cost': 19279.42,
                    'quantity': 1,
                    'value': 19279.42,
                },
                {
                    'unit_cost': 16580.33,
                    'quantity': 1,
                    'value': 16580.33,
                },
            ],
        )

    def test_import_case_04(self):
        """ Case 4, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            without advances
        """
        self._test_import(
            [],
            [
                {
                    'unit_cost': 19250.0,
                    'value': 96250.0,
                },
                {
                    'unit_cost': 16555.0,
                    'value': 165550.0,
                },
            ],
        )

    def test_import_case_05(self):
        """ Case 5, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            partial quantity with single advance on the whole amount
        """
        self._test_import(
            [
                {
                    'amount': 6800.0,
                    'currency_rate': 38.0,
                    'reconciled': False,
                    'amount_residual': 2150.0,
                },
            ],
            [
                {
                    'unit_cost': 19000.0,
                    'quantity': 5,
                    'value': 95000.0,
                },
                {
                    'unit_cost': 16340.0,
                    'quantity': 5,
                    'value': 81700.0,
                },
            ],
        )

    def test_import_case_06(self):
        """ Case 6, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA

            partial quantity with single advance on partial amount
        """
        self._test_import(
            [
                {
                    'amount': 3000.0,
                    'currency_rate': 38.0,
                    'reconciled': True,
                },
            ],
            [
                {
                    'unit_cost': 19088.71,
                    'quantity': 5,
                    'value': 95443.55,
                },
                {
                    'unit_cost': 16416.29,
                    'quantity': 5,
                    'value': 82081.45,
                },
            ],
        )

    def test_import_case_07(self):
        # single advance with amount more that whole amount
        self._test_import(
            [
                {
                    'amount': 10000.0,
                    'currency_rate': 38.0,
                    'reconciled': False,
                    'amount_residual': 3200.0,
                },
            ],
            [
                {
                    'unit_cost': 19000.0,
                    'value': 95000.0,
                },
                {
                    'unit_cost': 16340.0,
                    'value': 163400.0,
                },
            ],
        )

    def test_import_case_08(self):
        # two advances with amount more that whole amount
        self._test_import(
            [
                {
                    'amount': 4000.0,
                    'currency_rate': 40.0,
                    'reconciled': True,
                },
                {
                    'amount': 5000.0,
                    'currency_rate': 41.0,
                    'reconciled': False,
                    'amount_residual': 2200.0,
                },
            ],
            [
                {
                    'unit_cost': 20205.88,
                    'product_uom_qty': 5,
                    'quantity': 4,
                    'value': 80823.52,
                },
                {
                    'unit_cost': 17377.06,
                    'product_uom_qty': 10,
                    'quantity': 9,
                    'value': 156393.54,
                },
                {
                    'unit_cost': 20205.89,
                    'quantity': 1,
                    'value': 20205.89,
                },
                {
                    'unit_cost': 17377.05,
                    'quantity': 1,
                    'value': 17377.05,
                },
            ],
        )

    def test_import_case_09(self):
        # two advances with partial amount
        self._test_import(
            [
                {
                    'amount': 1000.0,
                    'currency_rate': 40.0,
                    'reconciled': True,
                },
                {
                    'amount': 3000.0,
                    'currency_rate': 41.0,
                    'reconciled': True,
                },
            ],
            [
                {
                    'unit_cost': 19911.76,
                    'product_uom_qty': 5,
                    'quantity': 4,
                    'value': 79647.04,
                },
                {
                    'unit_cost': 17124.12,
                    'product_uom_qty': 10,
                    'quantity': 9,
                    'value': 154117.08,
                },
                {
                    'unit_cost': 19911.78,
                    'quantity': 1,
                    'value': 19911.78,
                },
                {
                    'unit_cost': 17124.1,
                    'quantity': 1,
                    'value': 17124.1,
                },
            ],
        )

    def test_import_case_10(self):
        # two purchase orders with the same single advance on partial amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 4000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
            [
                [
                    {
                        'unit_cost': 19117.65,
                        'product_uom_qty': 5,
                        'quantity': 4,
                        'value': 76470.6,
                    },
                    {
                        'unit_cost': 16441.18,
                        'product_uom_qty': 10,
                        'quantity': 9,
                        'value': 147970.62,
                    },
                    {
                        'unit_cost': 19117.64,
                        'quantity': 1,
                        'value': 19117.64,
                    },
                    {
                        'unit_cost': 16441.14,
                        'quantity': 1,
                        'value': 16441.14,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
        )

    def test_import_case_11(self):
        # two purchase orders with the same two advances on partial amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 4000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 1000.0,
                        'currency_rate': 38.0,
                        'reconciled': True,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18970.59,
                        'product_uom_qty': 5,
                        'quantity': 4,
                        'value': 75882.36,
                    },
                    {
                        'unit_cost': 16314.71,
                        'product_uom_qty': 10,
                        'quantity': 9,
                        'value': 146832.39,
                    },
                    {
                        'unit_cost': 18970.58,
                        'quantity': 1,
                        'value': 18970.58,
                    },
                    {
                        'unit_cost': 16314.67,
                        'quantity': 1,
                        'value': 16314.67,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
        )

    def test_import_case_12(self):
        # two purchase orders with the same ane advance on full and partial amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 1200.0,
                    },
                ],
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                        'amount_forced': 1200.0,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 159200.0,
                        'value': 159200.0,
                    },
                ],
            ],
        )

    def test_import_case_13(self):
        # two purchase orders with the same two advances on full and partial amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 5000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 4000.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 2200.0,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18632.35,
                        'product_uom_qty': 5,
                        'quantity': 4,
                        'value': 74529.4,
                    },
                    {
                        'unit_cost': 16023.82,
                        'product_uom_qty': 10,
                        'quantity': 9,
                        'value': 144214.38,
                    },
                    {
                        'unit_cost': 18632.36,
                        'quantity': 1,
                        'value': 18632.36,
                    },
                    {
                        'unit_cost': 16023.86,
                        'quantity': 1,
                        'value': 16023.86,
                    },
                ],
                [
                    # advance reconciled - can not validate picking
                ],
            ],
        )

    def test_import_case_14(self):
        # two purchase orders with the same ane advance on full amount for both
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 20000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 13200.0,
                    },
                ],
                [
                    {
                        'amount': 20000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 9200.0,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 148000.0,
                        'value': 148000.0,
                    },
                ],
            ],
        )

    def test_import_case_15(self):
        # two purchase orders with the same two advances on full amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 1200.0,
                    },
                    {
                        'amount': 2800.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 2800.0,
                    },
                ],
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 2800.0,
                        'currency_rate': 38.0,
                        'reconciled': True,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 150800.0,
                        'value': 150800.0,
                    },
                ],
            ],
            skip_check_advances_reconciliation=True,
        )

    def test_import_case_16(self):
        # two purchase orders with the same two advances on full amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 1200.0,
                    },
                    {
                        'amount': 4000.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 4000.0,
                    },
                ],
                [
                    {
                        'amount': 8000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 2800.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 1200.0,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 150800.0,
                        'value': 150800.0,
                    },
                ],
            ],
            skip_check_advances_reconciliation=True,
        )

    def test_import_case_17(self):
        # two purchase orders with the same three advances on part amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 7000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 200.0,
                    },
                    {
                        'amount': 1000.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 1000.0,
                    },
                    {
                        'amount': 2000.0,
                        'currency_rate': 39.0,
                        'reconciled': False,
                        'amount_residual': 2000.0,
                    },
                ],
                [
                    {
                        'amount': 7000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 1000.0,
                        'currency_rate': 38.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 2000.0,
                        'currency_rate': 39.0,
                        'reconciled': True,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 156200.0,
                        'value': 156200.0,
                    },
                ],
            ],
            skip_check_advances_reconciliation=True,
        )

    def test_import_case_18(self):
        # two purchase orders with the same three advances on full amount
        self._test_import_two_orders(
            [
                [
                    {
                        'amount': 7000.0,
                        'currency_rate': 37.0,
                        'reconciled': False,
                        'amount_residual': 200.0,
                    },
                    {
                        'amount': 2000.0,
                        'currency_rate': 38.0,
                        'reconciled': False,
                        'amount_residual': 2000.0,
                    },
                    {
                        'amount': 2000.0,
                        'currency_rate': 39.0,
                        'reconciled': False,
                        'amount_residual': 2000.0,
                    },
                ],
                [
                    {
                        'amount': 7000.0,
                        'currency_rate': 37.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 1000.0,
                        'currency_rate': 38.0,
                        'reconciled': True,
                    },
                    {
                        'amount': 2000.0,
                        'currency_rate': 39.0,
                        'reconciled': False,
                        'amount_residual': 200.0,
                    },
                ],
            ],
            [
                [
                    {
                        'unit_cost': 18500.0,
                        'value': 92500.0,
                    },
                    {
                        'unit_cost': 15910.0,
                        'value': 159100.0,
                    },
                ],
                [
                    {
                        'unit_cost': 153600.0,
                        'value': 153600.0,
                    },
                ],
            ],
            skip_check_advances_reconciliation=True,
        )

    def test_import_case_19(self):
        advances_info = [
            {
                'amount': 10.0,
                'currency_rate': 38.0,
                'reconciled': True,
            },
            {
                'amount': 150.0,
                'currency_rate': 37.7094,
                'reconciled': False,
                'amount_residual': 10.0,
            },
        ]

        svl_info = [
            {
                'unit_cost': 377.29,
                'product_uom_qty': 10,
                'quantity': 9,
                'value': 3395.61,
            },
            {
                'unit_cost': 377.29,
                'product_uom_qty': 5,
                'quantity': 4,
                'value': 1509.16,
            },
            {
                'unit_cost': 377.27,
                'quantity': 1,
                'value': 377.27,
            },
            {
                'unit_cost': 377.28,
                'quantity': 1,
                'value': 377.28,
            },
        ]

        # create advance payments
        payments = self._create_advance_payments(advances_info)

        # create and validate purchase order
        purchase_order, stock_picking = self._create_import_purchase_order(
            advances_info,
            [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 10,
                    'price_unit': 10.0,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 5,
                    'price_unit': 10.0,
                }),
            ],
        )

        # write customs declaration info
        stock_picking.write({
            'customs_declaration_date': self.customs_declaration_date,
            'customs_declaration_currency_rate': 39.0,
        })

        self.assertEqual(len(stock_picking.cd_can_be_advance_ids), len(advances_info))
        for line in stock_picking.cd_can_be_advance_ids:
            stock_picking.advance_line_ids += line

        # validate and check picking
        self._validate_and_check_stock_picking(
            purchase_order,
            stock_picking,
            payments,
            advances_info,
            svl_info,
        )

    def test_import_case_20(self):
        """ Case 7, COGS імпорт (SP)
            https://docs.google.com/spreadsheets/d/1FLt2OyCCAzCxJGEXg0QBmz3K4ftuIS02RXeAtP3ZpCA
        """
        advances_info = [
            {
                'amount': 1500.0,
                'currency_rate': 36.834,
                'reconciled': False,
                'amount_residual': 229.29,
            },
        ]

        svl_info = [
            {
                'unit_cost': 653.07,
                'product_uom_qty': 71.67,
                'quantity': 70.67,
                'value': 46152.46,
            },
            {
                'unit_cost': 652.87,
                'quantity': 1,
                'value': 652.87,
            },
        ]

        # create advance payments
        payments = self._create_advance_payments(advances_info)

        # create and validate purchase order
        purchase_order, stock_picking = self._create_import_purchase_order(
            advances_info,
            [
                Command.create({
                    'product_id': self.product_3.id,
                    'product_qty': 71.67,
                    'price_unit': 17.73,
                }),
            ],
        )

        # write customs declaration info
        stock_picking.write({
            'customs_declaration_date': self.customs_declaration_date,
            'customs_declaration_currency_rate': 39.0,
        })

        self.assertEqual(len(stock_picking.cd_can_be_advance_ids), len(advances_info))
        for line in stock_picking.cd_can_be_advance_ids:
            stock_picking.advance_line_ids += line

        # validate and check picking
        self._validate_and_check_stock_picking(
            purchase_order,
            stock_picking,
            payments,
            advances_info,
            svl_info,
        )

    def test_different_product_types_in_import_order(self):
        products = [
            self.product_1,
            self.product_2,
            self.product_consu_1,
            self.product_consu_2,
            self.product_service_1,
            self.product_service_2,
        ]

        # for each combination
        for size in range(len(products) + 1):
            for subset in itertools.combinations(products, size):
                if not subset:
                    continue

                # create purchase order
                purchase_order = self.env['purchase.order'].create({
                    'partner_id': self.partner_a.id,
                    'date_order': fields.Date.today(),
                    'currency_id': self.currency_usd.id,
                    'is_import': True,

                    'order_line': [
                        Command.create({
                            'product_id': product.id,
                            'product_qty': 1,
                            'price_unit': 100,
                        })
                        for product in subset
                    ]
                })

                # contains different product types
                if (
                    len(subset) > 1
                    and list(filter(lambda x: x.type in ('product', 'consu'), subset))
                    and list(filter(lambda x: x.type not in ('product', 'consu'), subset))
                ):
                    try:
                        purchase_order.button_confirm()
                        self.fail()
                    except UserError:
                        pass
                else:
                    purchase_order.button_confirm()

    def test_import_services(self):
        # create advance payments
        payments = self._create_advance_payments([
            {
                'amount': 1000.0,
                'currency_rate': 40.0,
                'reconciled': True,
            },
            {
                'amount': 3000.0,
                'currency_rate': 41.0,
                'reconciled': True,
            },
        ])

        # create purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': fields.Date.today(),
            'currency_id': self.currency_usd.id,
            'is_import': True,

            'order_line': [
                Command.create({
                    'product_id': self.product_service_1.id,
                    'product_qty': 5,
                    'price_unit': 1000,
                }),
            ],
        })

        # confirm purchase order
        # (there is no stock picking)
        purchase_order.button_confirm()
        self.assertFalse(purchase_order.picking_ids)

        # create a vendor bill
        # (it should be marked as import by default)
        action = purchase_order.action_create_invoice()
        vendor_bill = self.env[action['res_model']].browse(action['res_id'])

        self.assertTrue(vendor_bill)
        self.assertTrue(vendor_bill.is_import_vendor_bill)

        self.assertEqual(len(vendor_bill.line_ids), 2)
        self.assertEqual(len(vendor_bill.import_available_advance_ids), 2)
        self.assertEqual(len(vendor_bill.import_advances_ids), 0)

        self.assertEqual(
            vendor_bill.line_ids[0].balance,
            vendor_bill.company_currency_id.round(1000.0 * 5 * self.currency_usd.inverse_rate),
        )

        # change customs declaration currency rate
        vendor_bill.write({
            'invoice_date': self.customs_declaration_date,
            'cd_date': self.customs_declaration_date,
            'cd_currency_rate': 38.5,
        })

        self.assertEqual(
            vendor_bill.line_ids[0].balance,
            1000.0 * 5 * 38.5,
        )

        # add advances
        vendor_bill.write({
            'import_stored_advance_ids': [Command.set(vendor_bill.import_available_advance_ids.ids)],
        })

        self.assertEqual(
            vendor_bill.line_ids[0].balance,
            (1000.0 * 40.0) + (3000.0 * 41.0) + (1000.0 * 38.5),
        )

        # confirm vendor bill
        vendor_bill.action_post()

        self.assertFalse(vendor_bill.line_ids[1].reconciled)
        self.assertTrue(payments[0].line_ids[1].reconciled)
        self.assertEqual(len(payments[0].line_ids[1].matched_debit_ids), 0)
        self.assertEqual(len(payments[0].line_ids[1].matched_credit_ids), 1)
        self.assertEqual(payments[0].line_ids[1].matched_credit_ids[0].credit_move_id, vendor_bill.line_ids[1])
        self.assertTrue(payments[1].line_ids[1].reconciled)
        self.assertEqual(len(payments[1].line_ids[1].matched_debit_ids), 0)
        self.assertEqual(len(payments[1].line_ids[1].matched_credit_ids), 1)
        self.assertEqual(payments[1].line_ids[1].matched_credit_ids[0].credit_move_id, vendor_bill.line_ids[1])

    def _test_import(self, advances_info, svl_info):
        # create advance payments
        payments = self._create_advance_payments(advances_info)

        # create and validate purchase order
        purchase_order, stock_picking = self._create_import_purchase_order(
            advances_info,
            [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 5,
                    'price_unit': 500,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 10,
                    'price_unit': 430,
                }),
            ],
        )

        # write customs declaration info
        stock_picking.write({
            'customs_declaration_date': self.customs_declaration_date,
            'customs_declaration_currency_rate': 38.5,
            'customs_declaration_line_ids': [
                Command.create({
                    'product_id': self.product_landed_cost.id,
                    'description': 'послуги доставки',
                    'amount': 15000,
                }),
            ],
        })

        self.assertEqual(len(stock_picking.cd_can_be_advance_ids), len(advances_info))
        for line in stock_picking.cd_can_be_advance_ids:
            stock_picking.advance_line_ids += line

        # validate and check picking
        self._validate_and_check_stock_picking(
            purchase_order,
            stock_picking,
            payments,
            advances_info,
            svl_info,
        )

        # create and check landed cost
        landed_cost_action = stock_picking.action_create_landed_cost()
        self.assertFalse(not landed_cost_action)

        landed_cost = self.env[landed_cost_action['res_model']].browse(landed_cost_action['res_id'])
        self.assertFalse(not landed_cost)
        self.assertEqual(landed_cost.state, 'draft')
        self.assertEqual(landed_cost.date, stock_picking.customs_declaration_date)
        self.assertEqual(landed_cost.target_model, 'picking')
        self.assertEqual(1, len(landed_cost.picking_ids))
        self.assertEqual(landed_cost.picking_ids, stock_picking)
        self.assertEqual(1, len(landed_cost.cost_lines))
        self.assertRecordValues(landed_cost.cost_lines, [
            {
                'name': stock_picking.customs_declaration_line_ids[0].description,
                'product_id': stock_picking.customs_declaration_line_ids[0].product_id.id,
                'price_unit': stock_picking.customs_declaration_line_ids[0].amount,
            },
        ])

    def _test_import_two_orders(self, advances_info, svl_info, skip_check_advances_reconciliation=False):
        # create advance payments
        payments = self._create_advance_payments(advances_info[0])

        orders_info = []

        # create and validate purchase orders
        orders_info.append(
            self._create_import_purchase_order(
                advances_info[0],   # use first here
                [
                    Command.create({
                        'product_id': self.product_1.id,
                        'product_qty': 5,
                        'price_unit': 500,
                    }),
                    Command.create({
                        'product_id': self.product_2.id,
                        'product_qty': 10,
                        'price_unit': 430,
                    }),
                ],
            )
        )

        orders_info.append(
            self._create_import_purchase_order(
                advances_info[0],   # use first here
                [
                    Command.create({
                        'product_id': self.product_consu_1.id,
                        'product_qty': 1,
                        'price_unit': 4000,
                    }),
                ],
            )
        )

        # firstly, write customs declaration info
        for i, order_info in enumerate(orders_info):
            stock_picking = order_info[1]

            # link advances
            stock_picking.write({
                'customs_declaration_date': self.customs_declaration_date,
                'customs_declaration_currency_rate': 40 + i,
            })
            self.assertEqual(len(stock_picking.cd_can_be_advance_ids), len(advances_info[0]))   # use first here
            stock_picking.advance_line_ids += stock_picking.cd_can_be_advance_ids

        # then validate and check first picking
        for i, order_info in enumerate(orders_info):
            purchase_order = order_info[0]
            stock_picking = order_info[1]

            self._validate_and_check_stock_picking(
                purchase_order,
                stock_picking,
                payments,
                advances_info[i],
                svl_info[i],
                break_on_empty_advance=True,
                skip_check_advances_reconciliation=skip_check_advances_reconciliation,
                skip_check_stock_reconciliation=(i == 1),   # skip for second order (it is consumed product)
            )

    def _create_advance_payments(self, advances_info):
        payments = []

        for i, advance_info in enumerate(advances_info):
            pay_line = self.create_contract_bank_statement_line(
                partner=self.partner_a,
                amount=-advance_info['amount'] * advance_info['currency_rate'],
                date=fields.Date.today() - timedelta(days=3 * (len(advances_info) - i)),
                currency=self.currency_usd,
                amount_currency=-advance_info['amount'],
            )
            payment_move = self.validate_statement_line(pay_line)

            self.assertEqual(payment_move.state, 'posted')

            payments.append(payment_move)

        return payments

    def _create_import_purchase_order(self, advances_info, lines):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': fields.Date.today() - timedelta(days=len(advances_info) + 2),
            'currency_id': self.currency_usd.id,
            'order_line': lines,
            'is_import': True,
        })

        # confirm purchase order
        purchase_order.button_confirm()
        stock_picking = purchase_order.picking_ids
        self.assertEqual(len(stock_picking), 1)
        self.assertEqual(len(stock_picking.move_ids), len(purchase_order.order_line))

        # return records
        return purchase_order, stock_picking

    def _validate_and_check_stock_picking(
            self,
            purchase_order,
            stock_picking,
            payments,
            advances_info,
            svl_info,
            break_on_empty_advance=False,
            skip_post_bill=False,
            skip_check_advances_reconciliation=False,
            skip_check_stock_reconciliation=False,
    ):
        # validate picking
        stock_picking = stock_picking.with_context(
            skip_immediate=True,
            skip_backorder=True,
            skip_sms=True,
        )

        # receive picking
        for i, move in enumerate(stock_picking.move_ids):
            quantity_done = None
            if svl_info:
                svl = svl_info[i]
                if 'product_uom_qty' in svl:
                    quantity_done = svl.pop('product_uom_qty')
                else:
                    quantity_done = svl.get('quantity')
            if not quantity_done:
                quantity_done = move.product_uom_qty
            move.quantity_done = quantity_done

        if not advances_info:
            try:
                stock_picking.button_validate()
                if break_on_empty_advance:
                    self.fail()
            except UserError:
                if break_on_empty_advance:
                    return
        else:
            stock_picking.button_validate()

        # check payments
        company_currency = stock_picking.company_currency_id
        for i, advance in enumerate(advances_info):
            if 'reconciled' in advance:
                payment = payments[i]
                payment_line = payment.line_ids[1]

                self.assertEqual(payment_line.reconciled, advance['reconciled'])
                self.assertEqual(company_currency.compare_amounts(payment_line.amount_residual, (advance.get('amount_residual') or 0.0) * advance['currency_rate']), 0)
                self.assertEqual(payment_line.amount_residual_currency, advance.get('amount_residual') or 0.0)

        # check SVL
        if svl_info:
            stock_valuation_layers = stock_picking.mapped('move_ids.stock_valuation_layer_ids')
            self.assertEqual(len(stock_picking.move_ids), len(stock_valuation_layers))
            self.assertEqual(len(stock_valuation_layers), len(svl_info))
            self.assertRecordValues(stock_valuation_layers, svl_info)

        # check a vendor bill
        if advances_info:
            # vendor bill created automatically!!!
            vendor_bill = stock_picking.vendor_bill_id
        else:
            # create vendor bill manually
            action = purchase_order.action_create_invoice()
            vendor_bill = self.env[action['res_model']].browse(action['res_id'])
            if not skip_post_bill:
                vendor_bill.action_post()

        self.assertTrue(vendor_bill)
        self.assertEqual(len(vendor_bill.invoice_line_ids), len(stock_picking.move_ids))
        self.assertEqual(len(vendor_bill.line_ids), len(stock_picking.move_ids) + 1)
        self.assertEqual(stock_picking.vendor_bill_id, vendor_bill)
        self.assertEqual(stock_picking, vendor_bill.stock_picking_id)
        self.assertEqual(purchase_order.currency_id, vendor_bill.currency_id)
        self.assertEqual(stock_picking.customs_declaration_date, vendor_bill.invoice_date)

        if not skip_post_bill and not skip_check_advances_reconciliation and advances_info:
            self.assertEqual(len(vendor_bill.line_ids[-1].matched_debit_ids), len(payments))
            self.assertEqual(len(vendor_bill.line_ids[-1].matched_credit_ids), 0)
            self.assertEqual(
                vendor_bill.line_ids[-1].reconciled,
                sum([a.get('amount_forced') or a['amount'] for a in advances_info]) >= vendor_bill.amount_total,
            )

        if svl_info:
            self.assertRecordValues(
                vendor_bill.invoice_line_ids,
                [
                    {
                        'stock_move_id': move.id,
                        'product_id': move.product_id.id,
                        'quantity': move.quantity_done,
                        'price_unit': move.purchase_line_id.price_unit,
                        'debit': svl_info[i]['value'],
                        'credit': 0,
                    }
                    for i, move in enumerate(stock_picking.move_ids)
                ],
            )

            if not skip_check_stock_reconciliation:
                stock_account_moves = stock_picking.mapped('move_ids.stock_valuation_layer_ids.account_move_id')
                self.assertEqual(len(stock_account_moves), len(vendor_bill.invoice_line_ids))

                for i, line in enumerate(vendor_bill.invoice_line_ids):
                    stock_account_move = stock_account_moves[i]
                    self.assertEqual(len(stock_account_move.line_ids), 2)

                    self.assertTrue(line.reconciled)
                    self.assertEqual(len(line.matched_debit_ids), 0)
                    self.assertEqual(len(line.matched_credit_ids), 1)
                    self.assertEqual(line.matched_credit_ids[0].credit_move_id, stock_account_move.line_ids[0])

                    self.assertTrue(stock_account_move.line_ids[0].reconciled)
                    self.assertEqual(len(stock_account_move.line_ids[0].matched_debit_ids), 1)
                    self.assertEqual(stock_account_move.line_ids[0].matched_debit_ids[0].debit_move_id, line)
                    self.assertEqual(len(stock_account_move.line_ids[0].matched_credit_ids), 0)

                    self.assertFalse(stock_account_move.line_ids[1].reconciled)
                    self.assertEqual(len(stock_account_move.line_ids[1].matched_debit_ids), 0)
                    self.assertEqual(len(stock_account_move.line_ids[1].matched_credit_ids), 0)

                    self.assertEqual(line.product_id, stock_account_move.line_ids[0].product_id)
                    self.assertEqual(line.quantity, stock_account_move.line_ids[0].quantity)
                    self.assertEqual(line.amount_currency, -stock_account_move.line_ids[0].amount_currency)
                    self.assertEqual(line.balance, -stock_account_move.line_ids[0].balance)

        #
        # @TODO: test purchase order paid/residual amount widget
        #

        if not skip_post_bill:
            try:
                # all done pickings already invoiced
                purchase_order.action_create_invoice()
                self.fail()
            except UserError:
                pass
