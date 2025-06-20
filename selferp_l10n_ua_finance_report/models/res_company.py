from odoo import api, models

from .. hooks import create_analytic_operating_expenses


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        # create company records
        records = super().create(vals_list)

        # create analytic plan
        create_analytic_operating_expenses(self.env, records)

        # return created records
        return records
