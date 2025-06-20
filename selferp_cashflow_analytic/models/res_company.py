from odoo import models, api

from ..hooks import create_analytic_plan_cash_flow


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        # create company records
        records = super().create(vals_list)

        # create analytic plan
        create_analytic_plan_cash_flow(self.env, records)

        # return created records
        return records
