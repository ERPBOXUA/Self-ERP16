import logging

from odoo import fields, models


_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_vat_partner_id = fields.Many2one(
        related='pos_config_id.vat_partner_id',
        readonly=False,
    )
