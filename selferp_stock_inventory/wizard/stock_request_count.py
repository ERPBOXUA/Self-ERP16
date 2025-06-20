from odoo import models, Command, _


class StockRequestCount(models.TransientModel):
    _inherit = 'stock.request.count'

    def action_create_inventory(self):
        self.ensure_one()

        self.action_request_count()

        # create inventories
        StockInventory = self.env['stock.inventory']
        inventories = StockInventory.browse()

        for company in list(self.quant_ids.mapped('company_id')) + [False]:
            lines = []
            for quant in self.quant_ids.filtered(lambda q: q.company_id == company if company else (not q.company_id)):
                lines.append(
                    Command.create({
                        'stock_quant_id': quant.id,
                        'product_id': quant.product_id.id,
                        'quantity': quant.quantity,
                        'inventory_quantity': quant.quantity if self.set_count == 'set' else 0,
                    })
                )
            if not lines:
                continue

            inventories += StockInventory.create({
                'company_id': company.id if company else self.env.company.id,
                'inventory_date': self.inventory_date,
                'user_id': self.user_id.id,
                'inventory_line_ids': lines,
            })

        # open created inventories
        if inventories:
            if len(inventories) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _("Inventory"),
                    'res_model': 'stock.inventory',
                    'res_id': inventories.id,
                    'view_mode': 'form',
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _("Inventories"),
                    'res_model': 'stock.inventory',
                    'domain': [('id', 'in', inventories.ids)],
                    'view_mode': 'tree,form',
                }
