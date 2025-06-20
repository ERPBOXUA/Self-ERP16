from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrJob(models.Model):
    _inherit = 'hr.job'

    job_class_id = fields.Many2one(
        comodel_name='hr.job.class',
        ondelete='restrict',
        string="Job Class",
    )

    @api.constrains('job_class_id')
    def _check_job_class_id(self):
        for rec in self:
            if rec.job_class_id and rec.job_class_id.child_ids:
                raise ValidationError(_("You must select a single profession (lowest level of hierarchy)"))
