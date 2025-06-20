from odoo import fields, models, api, _


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    asset_id = fields.Many2one(
        comodel_name='account.asset',
        compute='_compute_asset_id',
        string="Asset",
    )

    def _compute_asset_id(self):
        for record in self:
            assets_ids = self.env['account.asset'].search([('equipment_id', '=', record.id)], limit=1).ids
            record.asset_id = assets_ids and assets_ids[0] or None

    def action_show_asset(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Asset"),
            'res_model': self.asset_id._name,
            'res_id': self.asset_id.id,
            'view_mode': 'form',
        }
