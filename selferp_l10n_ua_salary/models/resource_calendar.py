from odoo import models, fields


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    is_service = fields.Boolean(
        string="Service Calendar",
        default=False,
    )

    def unlink(self):
        service = self.filtered(lambda rec: rec.is_service)
        super(ResourceCalendar, self - service).unlink()
