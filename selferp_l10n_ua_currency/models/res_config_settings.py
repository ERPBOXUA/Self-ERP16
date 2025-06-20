from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    income_exchange_difference_account_id = fields.Many2one(
        related='company_id.income_exchange_difference_account_id',
        string="Gain from FX difference",
        readonly=False,
    )
    expense_exchange_difference_account_id = fields.Many2one(
        related='company_id.expense_exchange_difference_account_id',
        string="Loss from FX difference",
        readonly=False,
    )
    bank_commission_account_id = fields.Many2one(
        related='company_id.bank_commission_account_id',
        string="Bank commission account",
        readonly=False,
    )
    transit_in_national_currency_account_id = fields.Many2one(
        related='company_id.transit_in_national_currency_account_id',
        string="Transit account in national currency",
        readonly=False,
    )
    transit_in_foreign_currency_account_id = fields.Many2one(
        related='company_id.transit_in_foreign_currency_account_id',
        string="Transit account in foreign currency",
        readonly=False,
    )
