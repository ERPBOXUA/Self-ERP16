from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vehicle = fields.Char(
        string="Vehicle",
    )

    vehicle_carrier_id = fields.Many2one(
        comodel_name='res.partner',
        string="Vehicle carrier",
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        string="Driver",
    )
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
    )
    loading_point_id = fields.Many2one(
        comodel_name='res.partner',
        string="Loading point",
    )
    unloading_point_id = fields.Many2one(
        comodel_name='res.partner',
        string="Unloading point",
    )

    def action_print_report(self):
        self.ensure_one()
        form = self.env.ref('selferp_l10n_ua_consignment_note.stock_picking_report_ttn')

        return {
            'name': form.name,
            'type': 'ir.actions.report',
            'report_name': form.report_name,
            'report_type': form.report_type,
            'report_file': form.report_file,
            'context': dict(self.env.context, active_ids=self.ids),
        }
