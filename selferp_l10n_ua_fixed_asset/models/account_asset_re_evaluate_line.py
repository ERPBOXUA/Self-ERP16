from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountAssetReEvaluateLine(models.Model):
    _name = 'account.asset.re_evaluate.line'
    _description = "Re-evaluate Lines"
    _order = 'asset_id, id'

    asset_id = fields.Many2one(
        comodel_name='account.asset',
        ondelete='cascade',
        required=True,
        readonly=True,
        index=True,
    )
    re_evaluate_move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string="Re-evaluate Move Line",
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='asset_id.currency_id',
    )
    value_re_evaluate_move_line = fields.Monetary(
        related='re_evaluate_move_line_id.balance',
        string="Balance",
    )
    value_re_evaluate = fields.Monetary(
        compute='_compute_value_re_evaluate',
        store=True,
        readonly=False,
        string="Value",
    )

    @api.depends('re_evaluate_move_line_id.balance')
    def _compute_value_re_evaluate(self):
        for record in self:
            record.value_re_evaluate = record.re_evaluate_move_line_id.balance

    @api.constrains('value_re_evaluate')
    def _check_value_re_evaluate(self):
        for record in self:
            if record.value_re_evaluate > record.value_re_evaluate_move_line:
                raise UserError(_("Value Re-evaluate must be less than Value Re-evaluate Move Line"))
