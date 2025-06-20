from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install')
class TestStockInventorySequence(TransactionCase):

    def test_companies_sequence_stock_inventory(self):
        companies = self.env['res.company'].search_count([('sequence_stock_inventory_id', '=', False)])
        self.assertFalse(companies)

    def test_create_unlink_company(self):
        company = self.env['res.company'].create({
            'name': "HO company",
        })

        self.assertTrue(company.sequence_stock_inventory_id)
        self.assertEqual(company, company.sequence_stock_inventory_id.company_id)
        company_sequence_stock_inventory_id = company.sequence_stock_inventory_id.id

        self.env['stock.rule'].search([('company_id', '=', company.id)]).unlink()
        self.env['stock.warehouse'].search([('company_id', '=', company.id)]).unlink()
        self.env['stock.picking.type'].search([('company_id', '=', company.id)]).unlink()
        if 'project.project' in self.env:
            self.env['project.project'].search([('company_id', '=', company.id)]).unlink()

        company.unlink()

        is_unlink_company_sequence = self.env['ir.sequence'].search_count(
            [('id', '=', company_sequence_stock_inventory_id)],
        )
        self.assertFalse(is_unlink_company_sequence)
