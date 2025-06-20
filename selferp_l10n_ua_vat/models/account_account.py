from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    first_event = fields.Boolean(
        string="The first event",
        default=False,
        index=True,
        help="Check the box if the account should track the first VAT event.",
    )
