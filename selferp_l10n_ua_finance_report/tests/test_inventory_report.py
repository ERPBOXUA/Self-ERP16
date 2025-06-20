from freezegun import freeze_time

from odoo import fields, Command
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestInventoryReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref or 'l10n_ua.l10n_ua_psbo_chart_template')

        cls.inventory_report = cls.env.ref('selferp_l10n_ua_finance_report.account_report_inventory_report')
        cls.company = cls.company_data['company']
        cls.date_move = fields.Date.from_string('2024-01-02')
        cls.stock_location = cls.env['stock.location'].create(
            {
                'name': 'test',
                'usage': 'internal',
                'location_id': cls.env.ref('stock.stock_location_locations').id,
                'company_id': cls.company.id,
            }
        )
        cls.supplier_location = cls.env['stock.location'].create(
            {
                'name': 'test',
                'usage': 'supplier',
                'location_id': cls.env.ref('stock.stock_location_suppliers').id,
                'company_id': cls.company.id,
            }
        )
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.product_bike = cls.env['product.product'].create(
            {
                'name': 'bike',
                'type': 'product',
                'cost_method': 'average',
                'detailed_type': 'product',
                'categ_id': cls.env.ref('product.product_category_all').id,
            }
        )
        cls.product_bike_2 = cls.env['product.product'].create(
            {
                'name': 'bike 2',
                'type': 'product',
                'cost_method': 'average',
                'detailed_type': 'product',
                'categ_id': cls.env.ref('product.product_category_all').id,
            }
        )

        cls.db_account = cls.env['account.account'].search(
            [('company_id', '=', cls.company.id), ('code', '=', '281000')],
            limit=1,
        )
        cls.cr_account = cls.env['account.account'].search(
            [('company_id', '=', cls.company.id), ('code', '=', '281100')],
            limit=1,
        )
        stock_valuation_account = cls.env['account.account'].create(
            {
                'name': 'Stock Valuation',
                'code': 'StockValuation',
                'account_type': 'asset_current',
                'reconcile': True,
            }
        )
        cls.product_bike.categ_id.write(
            {
                'property_stock_account_input_categ_id': cls.db_account.id,
                'property_stock_valuation_account_id': cls.cr_account.id,
                'property_stock_account_output_categ_id': stock_valuation_account.id,
                'property_valuation': 'real_time',
                'property_cost_method': 'fifo',
            }
        )

    @freeze_time('2024-01-02')
    def test_inventory_report(self):
        lines = [
            Command.create({'product_id': self.product_bike.id, 'debit': 100, 'account_id': self.db_account.id}),
            Command.create({'product_id': self.product_bike.id, 'credit': 100, 'account_id': self.cr_account.id}),
            Command.create({'product_id': self.product_bike_2.id, 'debit': 200, 'account_id': self.db_account.id}),
            Command.create({'product_id': self.product_bike_2.id, 'credit': 200, 'account_id': self.cr_account.id}),
        ]

        account_move = self.env['account.move'].create(
            {
                'move_type': 'entry',
                'date': self.date_move,
                'line_ids': lines,
            }
        )
        account_move.action_post()

        stock_move = self.env['stock.move'].create(
            {
                'name': '10 in',
                'date': self.date_move,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product_bike.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
                'price_unit': 10,
                'move_line_ids': [Command.create(
                    {
                        'product_id': self.product_bike.id,
                        'location_id': self.supplier_location.id,
                        'location_dest_id': self.stock_location.id,
                        'product_uom_id': self.uom_unit.id,
                        'qty_done': 10.0,
                    },
                )],
            },
        )
        stock_move._action_confirm()
        stock_move._action_done()

        options = self._generate_options(
            self.inventory_report,
            fields.Date.from_string('2024-01-01'),
            fields.Date.from_string('2024-01-31'),
        )
        options['unfold_all'] = True
        lines = self.inventory_report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name,   UoM, opening_qty, debit_qty, credit_qty, closing_qty, opening_balance, debit_balance, credit_balance, closing_balance,
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [
                ('Current Asset', '', 0.0, 10.0, -10.0, 0.0, '', 400, 400, ''),
                ('281000 Товари на складі', '', '', '', -10.0, -10.0, '', 300.00, 100.00, 200.00),
                ('bike', 'Units', '', '', -10.0, -10.0, '', 100.00, 100.00, ''),
                ('bike 2', 'Units', '', '', '', '', '', 200.00, '', 200.00),
                ('Total 281000 Товари на складі', '', '', '', -10.0, -10.0, '', 300.00, 100.00, 200.00),
                ('281100 Товари відвантажені зі складу', '', '', 10.0, '', 10.0, '', 100.00, 300.00, -200.00),
                ('bike', 'Units', '', 10.0, '', 10.0, '', 100.00, 100.00, ''),
                ('bike 2', 'Units', '', '', '', '', '', '', 200.00, -200.00),
                ('Total 281100 Товари відвантажені зі складу', '', '', 10.0, '', 10.0, '', 100.00, 300.00, -200.00),
                ('Total Current Asset', '', 0.0, 10.0, -10.0, 0.0, '', 400.00, 400.00, ''),
            ],
            options,
        )
