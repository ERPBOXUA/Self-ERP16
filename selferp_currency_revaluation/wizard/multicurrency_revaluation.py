from datetime import timedelta

from odoo import api, models, fields, Command, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class MulticurrencyRevaluationWizard(models.TransientModel):
    _inherit = 'account.multicurrency.revaluation.wizard'

    reverse_type = fields.Selection(
        selection=[
            ('reverse', "Reverse"),
            ('storno', "Storno"),
        ],
        required=True,
        compute_sudo=True,
        compute='_compute_accounting_values',
        inverse='_inverse_reverse_type',
        string="Reverse Type",
    )

    @api.depends('company_id')
    def _compute_accounting_values(self):
        for record in self:
            company = record.company_id
            record.journal_id = company.account_revaluation_journal_id or company.currency_exchange_journal_id
            record.expense_provision_account_id = company.expense_currency_exchange_account_id or company.account_revaluation_expense_provision_account_id
            record.income_provision_account_id = company.income_currency_exchange_account_id or company.account_revaluation_income_provision_account_id
            record.reverse_type = company.account_revaluation_reverse_type or 'storno'

    def _inverse_reverse_type(self):
        for record in self:
            record.company_id.sudo().account_revaluation_reverse_type = record.reverse_type

    @api.onchange('date')
    def _onchange_date(self):
        for record in self:
            if record.date:
                record.reversal_date = record.date + timedelta(days=1)

    def create_entries(self):
        """ Completely override method for adding storno support
            and skip reverse move creation for exchange difference
            lines (means when amount currency is 0)
        """
        self.ensure_one()

        # get and check lines
        move_vals = self.with_context(return_report_lines=True)._get_move_vals()
        if not move_vals['line_ids']:
            raise UserError(_("No provision needed was found."))

        AccountMove = self.env['account.move']

        # get report lines
        report_lines = move_vals.pop('report_lines')

        # create adjustment move
        move_vals['currency_revaluation'] = True
        adjustment_move = AccountMove.create(move_vals)
        adjustment_move.action_post()

        # create reverse move as storning record
        if self.reverse_type == 'storno':
            default_values = {
                'currency_revaluation': True,
                'is_storno': True,
                'ref': _("Storno of: %s", adjustment_move.ref),
            }
        else:
            default_values = {
                'currency_revaluation': True,
                'is_storno': False,
                'ref': _("Reversal of: %s", adjustment_move.ref),
            }

        # create reverse move
        reverse_move = adjustment_move._reverse_moves(default_values_list=[default_values])

        # remove zero currency amount lines
        lines = reverse_move.line_ids
        to_unlink = lines.browse()
        for i in range(len(report_lines)):
            report_line = report_lines[i]
            if any([
                c.get('expression_label') == 'balance_current' and reverse_move.company_currency_id.is_zero(c.get('no_format') or 0)
                for c in report_line.get('columns')
            ]):
                to_unlink += lines[i * 2] + lines[i * 2 + 1]
        if to_unlink:
            to_unlink.unlink()

        # post move if there is any line
        if reverse_move.line_ids:
            reverse_move.date = self.reversal_date
            reverse_move.action_post()
        else:
            reverse_move.unlink()

        # show an adjustment move form
        form = self.env.ref('account.view_move_form', False)
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        return {
            'type': 'ir.actions.act_window',
            'res_model': adjustment_move._name,
            'res_id': adjustment_move.id,
            'view_mode': 'form',
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'context': ctx,
        }

    @api.model
    def _get_move_vals(self):
        """ Completely override method for skip reverse move creation
            for exchange difference lines (means when amount currency is 0)
            and change labels
        """

        def _get_model_id(parsed_line, selected_model):
            for dummy, parsed_res_model, parsed_res_id in parsed_line:
                if parsed_res_model == selected_model:
                    return parsed_res_id

        def _get_adjustment_balance(line):
            for column in line.get('columns'):
                if column.get('expression_label') == 'adjustment':
                    return column.get('no_format')

        options = {**self._context['multicurrency_revaluation_report_options'], 'unfold_all': False}
        currency_rates = options['currency_rates']
        for currency_id, currency_values in currency_rates.items():
            currency_values['rate_inverse'] = 1.0 / (currency_values.get('rate') or 1.0)

        report = self.env.ref('account_reports.multicurrency_revaluation_report')
        included_line_id = report.line_ids.filtered(lambda l: l.code == 'multicurrency_included').id
        generic_included_line_id = report._get_generic_line_id('account.report.line', included_line_id)

        report_lines = report._get_lines(options)
        move_lines = []
        move_lines_info = []

        for report_line in report._get_unfolded_lines(report_lines, generic_included_line_id):
            parsed_line_id = report._parse_line_id(report_line.get('id'))
            balance = _get_adjustment_balance(report_line)
            # parsed_line_id[-1][-2] corresponds to res_model of the current line
            if (
                parsed_line_id[-1][-2] == 'account.account'
                and not self.env.company.currency_id.is_zero(balance)
            ):
                # remember report line for check externally
                move_lines_info.append(report_line)

                account_id = _get_model_id(parsed_line_id, 'account.account')
                currency_id = _get_model_id(parsed_line_id, 'res.currency')
                currency = self.env['res.currency'].browse(currency_id)

                move_lines.append(Command.create({
                    'name': _(
                        "Provision for %(for_cur)s (1 %(for_cur)s = %(rate).4f %(comp_cur)s)",
                        for_cur=currency.display_name,
                        comp_cur=self.env.company.currency_id.display_name,
                        rate=currency_rates[str(currency_id)]['rate_inverse'],
                    ),
                    'debit': balance if balance > 0 else 0,
                    'credit': -balance if balance < 0 else 0,
                    'amount_currency': 0,
                    'currency_id': currency_id,
                    'account_id': account_id,
                }))

                if balance < 0:
                    move_line_name = _("Expense Provision for %s", currency.display_name)
                else:
                    move_line_name = _("Income Provision for %s", currency.display_name)
                move_lines.append(Command.create({
                    'name': move_line_name,
                    'debit': -balance if balance < 0 else 0,
                    'credit': balance if balance > 0 else 0,
                    'amount_currency': 0,
                    'currency_id': currency_id,
                    'account_id': self.expense_provision_account_id.id if balance < 0 else self.income_provision_account_id.id,
                }))

        # prepare move values
        result = {
            'ref': _("Foreign currencies adjustment entry as of %s", format_date(self.env, self.date)),
            'journal_id': self.journal_id.id,
            'date': self.date,
            'line_ids': move_lines,
        }

        if self._context.get('return_report_lines'):
            result['report_lines'] = move_lines_info

        # return complete result
        return result
