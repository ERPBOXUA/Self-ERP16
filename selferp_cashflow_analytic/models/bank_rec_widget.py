from odoo import models, fields, api


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    cash_flow_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        related='st_line_id.cash_flow_analytic_account_id',
        # 'depends' is needed to make 'st_line_id' accessible in the onchange method (see below)
        depends=['st_line_id'],
        readonly=False,
        domain=[('cash_flow_article', '=', True)],
    )

    @api.onchange('cash_flow_analytic_account_id')
    def _onchange_cash_flow_analytic_account_id(self):
        # Since 'bank.rec.widget' model is not "standard" and doesn't allow to save value
        # of 'cash_flow_analytic_account_id'  via 'related' field, this hack is used to save changes of
        # 'cash_flow_analytic_account_id' directly into 'st_line_id'
        cash_flow_analytic_account = self.cash_flow_analytic_account_id
        if self.st_line_id.cash_flow_analytic_account_id != cash_flow_analytic_account:
            self.st_line_id.write({
                'cash_flow_analytic_account_id': cash_flow_analytic_account and cash_flow_analytic_account.id or None,
            })

    def js_action_reconcile_st_line(self, st_line_id, params):
        super().js_action_reconcile_st_line(st_line_id, params)
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)
        if st_line and st_line.cash_flow_analytic_account_id:
            line = st_line.move_id.line_ids.filtered(lambda l: l.account_id and l.account_id.account_type == 'asset_cash')
            if line:
                analytic_distribution = line.analytic_distribution or {}
                analytic_distribution.update({str(st_line.cash_flow_analytic_account_id.id): 100})
                line.analytic_distribution = analytic_distribution
                line.analytic_line_ids.unlink()
                line._create_analytic_lines()
