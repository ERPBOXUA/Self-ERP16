from datetime import timedelta

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install')
class TestStockInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'standard_price': 10.0,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'standard_price': 20.0,
        })
        (cls.product1 + cls.product2).categ_id.write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

    def test_stock_inventory(self):
        # create initial stock state
        stock_moves = self.env['stock.move'].create([
            {
                'name': 'test_1',
                'state': 'confirmed',
                'location_id': self.customer_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product1.id,
                'product_uom_qty': 10.0,
                'is_inventory': True,
                'move_line_ids': [
                    Command.create({
                        'product_id': self.product1.id,
                        'qty_done': 10,
                        'location_id': self.customer_location.id,
                        'location_dest_id': self.stock_location.id,
                    }),
                ],
            },
            {
                'name': 'test_1',
                'state': 'confirmed',
                'location_id': self.customer_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product2.id,
                'product_uom_qty': 20.0,
                'is_inventory': True,
                'move_line_ids': [
                    Command.create({
                        'product_id': self.product2.id,
                        'qty_done': 20,
                        'location_id': self.customer_location.id,
                        'location_dest_id': self.stock_location.id,
                    }),
                ],
            },
        ])
        stock_moves._action_done()

        # get appropriate quants
        quants = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', 'in', (self.product1.id, self.product2.id)),
        ])

        # create inventory
        today = fields.Date.today()
        inventory_date = today - timedelta(days=1)
        accounting_date = today - timedelta(days=3)
        stock_request_count = self.env['stock.request.count'].create({
            'inventory_date': inventory_date,
            'accounting_date': accounting_date,
            'quant_ids': quants,
        })
        
        stock_inventory_id = stock_request_count.action_create_inventory()['res_id']

        stock_inventory = self.env['stock.inventory'].search([('id', '=', stock_inventory_id)])

        # check inventory
        self.assertEqual(stock_inventory.name, 'New')
        self.assertEqual(stock_inventory.state, 'draft')
        self.assertEqual(len(stock_inventory.inventory_line_ids), 2)
        self.assertEqual(stock_inventory.stock_move_line_count, 2)
        self.assertEqual(stock_inventory.location_ids, self.stock_location)

        stock_inventory.inventory_line_ids[0].inventory_quantity = 30
        stock_inventory.inventory_line_ids[1].inventory_quantity = 40

        # confirm inventory and check state
        stock_inventory.action_confirm()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 30)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 40)

        self.assertRecordValues(stock_inventory.inventory_line_ids, [
            {
                'inventory_id': stock_inventory.id,
                'product_id': self.product1.id,
                'quantity': 10,
                'inventory_quantity': 30,
                'inventory_diff_quantity': 20,
            },
            {
                'inventory_id': stock_inventory.id,
                'product_id': self.product2.id,
                'quantity': 20,
                'inventory_quantity': 40,
                'inventory_diff_quantity': 20,
            },

        ])

        # check stock moves
        stock_move_lines = self.env['stock.move.line'].search(
            [
                ('stock_inventory_line_id', 'in', stock_inventory.inventory_line_ids.ids),
            ],
            order='id',
        )
        self.assertRecordValues(stock_move_lines, [
            {
                'stock_inventory_line_id': stock_inventory.inventory_line_ids[0].id,
                'qty_done': 20,
                'location_dest_id': self.stock_location.id,
            },
            {
                'stock_inventory_line_id': stock_inventory.inventory_line_ids[1].id,
                'qty_done': 20,
                'location_dest_id': self.stock_location.id,
            },
        ])

        # check account moves
        account_moves = self.env['account.move'].search([
            ('stock_move_id', 'in', stock_move_lines.move_id.ids),
        ])
        self.assertEqual(len(account_moves), 2)
        self.assertEqual(account_moves[0].date, stock_inventory.inventory_line_ids[0].stock_quant_id.accounting_date)
        self.assertEqual(account_moves[0].date, accounting_date)
        self.assertEqual(account_moves[1].date, stock_inventory.inventory_line_ids[1].stock_quant_id.accounting_date)
        self.assertEqual(account_moves[1].date, accounting_date)

    def test_stock_inventory_multi_company(self):
        company_1 = self.env['res.company'].create({'name': 'company_1'})

        company_2 = self.env['res.company'].create({'name': 'company_2'})

        stock_moves = self.env['stock.move'].create(
            [
                {
                    'name': 'test_1',
                    'company_id': company_1.id,
                    'state': 'confirmed',
                    'location_id': company_1.internal_transit_location_id.id,
                    'location_dest_id': company_1.internal_transit_location_id.id,
                    'product_id': self.product1.id,
                    'product_uom_qty': 10.0,
                    'is_inventory': True,
                    'move_line_ids': [
                        Command.create(
                            {
                                'product_id': self.product1.id,
                                'qty_done': 10,
                                'location_id': company_1.internal_transit_location_id.id,
                                'location_dest_id': company_1.internal_transit_location_id.id,
                            }
                        )
                    ],
                },
                {
                    'name': 'test_1',
                    'company_id': company_2.id,
                    'state': 'confirmed',
                    'location_id': company_2.internal_transit_location_id.id,
                    'location_dest_id': company_2.internal_transit_location_id.id,
                    'product_id': self.product1.id,
                    'product_uom_qty': 20.0,
                    'is_inventory': True,
                    'move_line_ids': [
                        Command.create(
                            {
                                'product_id': self.product1.id,
                                'qty_done': 20,
                                'location_id': company_2.internal_transit_location_id.id,
                                'location_dest_id': company_2.internal_transit_location_id.id,
                            }
                        )
                    ],
                },
            ]
        )
        stock_moves._action_done()

        quants = self.env['stock.quant'].search([('product_id', '=', self.product1.id)])

        stock_request_count = self.env['stock.request.count'].create({'quant_ids': quants})
        stock_request_count.action_create_inventory()

        stock_inventories = self.env['stock.inventory'].search([])

        self.assertEqual(len(stock_inventories), 2)
        self.assertEqual(len(stock_inventories[0].inventory_line_ids), 1)
        self.assertEqual(len(stock_inventories[1].inventory_line_ids), 1)
