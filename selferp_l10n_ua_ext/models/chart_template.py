from odoo import models

from ..hooks import _update_asset_account_type


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        self.ensure_one()

        res = super().generate_account(tax_template_ref, acc_template_ref, code_digits, company)

        _update_asset_account_type(self.env, company=company)

        return res
