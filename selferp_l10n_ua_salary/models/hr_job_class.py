from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrJobClass(models.Model):
    _name = 'hr.job.class'
    _description = "Job Classificator"
    _rec_names_search = ['code', 'name']

    name = fields.Char(
        string="Name",
        required=True,
    )

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
    )

    code_zkpptr = fields.Char(
        string="ZKPPTR Code",
    )

    issue_etkd = fields.Char(
        string="ETKD Issue",
    )

    issue_dkhp = fields.Char(
        string="DKHP Issue",
    )

    parent_id = fields.Many2one(
        comodel_name='hr.job.class',
        ondelete='restrict',
        string="Parent",
    )

    child_ids = fields.One2many(
        comodel_name='hr.job.class',
        inverse_name='parent_id',
        string="Subclasses",
    )

    related_job_ids = fields.Many2many(
        comodel_name='hr.job',
        string="Related Job Positions",
        compute='_compute_related_job_ids',
    )

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if rec.code and rec.parent_id and rec.parent_id.code and not rec.code.startswith(rec.parent_id.code):
                raise ValidationError(_("The job class code must contain the parent code as part of it"))

    def _compute_related_job_ids(self):
        HrJob = self.env['hr.job']
        for rec in self:
            rec.related_job_ids = HrJob.search([('job_class_id', '=', rec.id)])

    def name_get(self):
        return [(rec.id, '[%s] %s' % (rec.code, rec.name)) for rec in self]
