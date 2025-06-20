from odoo import Command
from odoo.tests import tagged

from .common import AccountTestCommon


@tagged('-at_install', 'post_install')
class TestSaleOrder(AccountTestCommon):

    def test_create_invoice_from_sale_order(self):
        sale = self.create_sale_order(
            partner=self.partner_a,
            products=[self.product_a],
            counts=[1],
            prices=[1],
        )
        self.confirm_sale_order(sale)

        sale.create_invoice_delivered()
        invoices = sale.mapped('invoice_ids')
        self.assertEqual(len(invoices), 1)

    @classmethod
    def create_sale_order(cls, partner, products, counts, prices, date_order=None):
        assert len(products) == len(counts), "Products and counts should have same count of elements"
        assert len(products) == len(prices), "Products and prices should have same count of elements"

        lines = [
            Command.create({
                'product_id': product.id,
                'product_uom_qty': counts[i],
                'price_unit': prices[i],
            })
            for i, product in enumerate(products)
        ]

        sale_order = cls.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': lines,
        })
        if date_order:
            cls.env.cr.execute('''
                UPDATE sale_order 
                   SET create_date = %s, 
                       date_order = %s    
            ''', (date_order, date_order))

        return sale_order

    @classmethod
    def confirm_sale_order(cls, sale_order, date_order=None):
        sale_order.action_confirm()
        if date_order:
            cls.env.cr.execute('''
                UPDATE sale_order 
                   SET date_order = %s    
            ''', (date_order,))
        assert sale_order.state == 'sale', "Sale order confirmation failed"
