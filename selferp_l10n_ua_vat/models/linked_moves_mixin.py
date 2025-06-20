from odoo import api, models, fields, _
from odoo.tools.misc import formatLang


class OrderLinkedMovesMixin(models.AbstractModel):
    _name = 'linked_moves.mixin'
    _description = "Linked moves (for sale/purchase order) mixin"

    move_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        compute='_compute_move_line_ids',
        string="Journal Items",
    )
    move_line_count = fields.Integer(
        compute='_compute_move_line_ids',
        string="Journal Items Count",
    )

    amount_paid = fields.Float(
        string="Paid",
        compute='_compute_paid_amounts',
        compute_sudo=True,
    )
    amount_paid_formatted = fields.Char(
        compute='_compute_paid_amounts',
        compute_sudo=True,
    )
    amount_outstanding_payment = fields.Float(
        string="Outstanding Payment",
        compute='_compute_paid_amounts',
        compute_sudo=True,
    )
    amount_outstanding_payment_formatted = fields.Char(
        compute='_compute_paid_amounts',
        compute_sudo=True,
    )

    @api.depends('invoice_ids', 'invoice_status')
    def _compute_move_line_ids(self):
        AccountMoveLine = self.env['account.move.line']
        for record in self:
            domain = record._get_move_lines_domain()
            lines = AccountMoveLine.search(domain)
            record.move_line_ids = lines
            record.move_line_count = len(lines)

    @api.depends('move_line_ids', 'amount_total')
    def _compute_paid_amounts(self):
        for record in self:
            amount_paid = 0.0

            if record.move_line_ids:
                move_lines = record.move_line_ids.filtered(lambda r: r.journal_id.type in ('cash', 'bank'))
                if move_lines:
                    if record.currency_id != record.company_id.currency_id:
                        amount_paid = -sum(move_lines.mapped('amount_currency')) * self._get_payment_amount_sign()
                    else:
                        amount_paid = (sum(move_lines.mapped('credit')) - sum(move_lines.mapped('debit'))) * self._get_payment_amount_sign()

            currency = record.currency_id or record.company_id.currency_id

            record.amount_paid = amount_paid
            record.amount_paid_formatted = formatLang(self.env, amount_paid, currency_obj=currency)
            record.amount_outstanding_payment = record.amount_total - amount_paid
            record.amount_outstanding_payment_formatted = formatLang(self.env, record.amount_outstanding_payment, currency_obj=currency)

    def action_view_journal_items(self):
        self.ensure_one()
        return {
            'name': _("Journal Items"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': self._get_move_lines_domain(),
        }

    def _update_amount_paid_totals(self):
        for record in self:
            currency = record.currency_id or record.company_id.currency_id

            record.tax_totals.update({
                'amount_paid': currency.round(record.amount_paid),
                'formatted_amount_paid': record.amount_paid_formatted,
                'amount_outstanding_payment': currency.round(record.amount_outstanding_payment),
                'formatted_amount_outstanding_payment': record.amount_outstanding_payment_formatted,
            })

    def _get_move_lines_domain(self):
        raise NotImplemented()

    @api.model
    def _get_payment_amount_sign(self):
        raise NotImplemented()
