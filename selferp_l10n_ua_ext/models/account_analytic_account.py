from odoo import models, fields


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    description = fields.Text(
        string="Description",
        translate=True,
    )
