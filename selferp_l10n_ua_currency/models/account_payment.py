from odoo import api, Command, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    currency_transactions = fields.Boolean(
        string="Currency Transactions",
        default=False,
        index=True,
    )
    interbank_currency_exchange_rate = fields.Float(
        string="Interbank currency exchange rate",
    )
    bank_commission = fields.Float(
        string="Bank commission",
    )
    nbu_currency_exchange_rate = fields.Float(
        string="NBU currency exchange rate"
    )
    interbank_and_nbu_difference = fields.Float(
        compute='_compute_interbank_and_nbu_difference',
        readonly=True,
        string="Differences between the Interbank exchange rate and the NBU"
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Company Currency",
    )

    currency_sell_date = fields.Date(
        string="Currency Sell Date",
    )

    currency_sell_date_rate = fields.Float(
        string="Currency Sell Date Rate",
    )

    currency_sell_date_difference = fields.Float(
        string="Currency Sell Date Difference",
        compute='_compute_currency_sell_date_difference',
    )

    # UI only trigger
    @api.onchange('currency_transactions')
    def _on_change_currency_transactions(self):
        self.ensure_one()
        if self.currency_transactions:
            if self.currency_id == self.company_id.currency_id:
                valutes = self.env['res.currency'].search([('id', '!=', self.company_id.currency_id.id)])
                if valutes:
                    self.currency_id = valutes[0]
        

    @api.onchange('interbank_currency_exchange_rate', 'nbu_currency_exchange_rate')
    @api.depends('interbank_currency_exchange_rate', 'nbu_currency_exchange_rate')
    def _compute_interbank_and_nbu_difference(self):
        for rec in self:
            rec.interbank_and_nbu_difference = rec.interbank_currency_exchange_rate - rec.nbu_currency_exchange_rate

    @api.onchange('currency_id', 'date')
    def _onchange_currency_rate(self):
        for record in self:
            rate = 0
            if record.currency_id and record.date:
                rate = record.currency_id.with_context(date=record.date).inverse_rate
            record.nbu_currency_exchange_rate = rate
            if not record.currency_sell_date:
                record.currency_sell_date = record.date

    @api.onchange('currency_id', 'currency_sell_date')
    def _onchange_currency_sell_date(self):
        for record in self:
            rate = 0
            if record.currency_id and record.date:
                rate = record.currency_id.with_context(date=record.currency_sell_date).inverse_rate
            record.currency_sell_date_rate = rate

    @api.onchange('currency_sell_date_rate', 'nbu_currency_exchange_rate')
    @api.depends('currency_sell_date_rate', 'nbu_currency_exchange_rate')
    def _compute_currency_sell_date_difference(self):
        for rec in self:
            rec.currency_sell_date_difference = rec.nbu_currency_exchange_rate - rec.currency_sell_date_rate

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        super_fields = super()._get_trigger_fields_to_synchronize()

        return super_fields + (
            'currency_transactions',
            'interbank_currency_exchange_rate',
            'bank_commission',
            'nbu_currency_exchange_rate',
            'interbank_and_nbu_difference',
            'currency_sell_date_rate',
            'currency_sell_date_difference',
        )

    def _create_currency_exchange_lines(self):
        self.ensure_one()
        if self.payment_type == 'inbound':
            account1_d = self.company_id.account_journal_payment_credit_account_id
            account1_с = self.company_id.transit_in_national_currency_account_id
            account2_d = self.company_id.bank_commission_account_id
            account2_с = self.company_id.transit_in_national_currency_account_id

            account3_dp = self.company_id.expense_exchange_difference_account_id
            account3_cp = self.company_id.transit_in_national_currency_account_id
            account3_dn = self.company_id.transit_in_national_currency_account_id
            account3_cn = self.company_id.income_exchange_difference_account_id

            rate = self.nbu_currency_exchange_rate
            amount_grn = self.amount * rate
            amount_currency = self.amount
        else:
            account1_d = self.company_id.account_journal_payment_debit_account_id
            account1_с = self.company_id.transit_in_foreign_currency_account_id
            account2_d = self.company_id.bank_commission_account_id
            account2_с = self.company_id.transit_in_foreign_currency_account_id

            account3_dp = self.company_id.transit_in_foreign_currency_account_id
            account3_cp = self.company_id.income_exchange_difference_account_id
            account3_dn = self.company_id.expense_exchange_difference_account_id
            account3_cn = self.company_id.transit_in_foreign_currency_account_id

            rate = self.interbank_currency_exchange_rate
            amount_grn = self.amount * rate - self.bank_commission
            amount_currency = 0

        line_vals_list = []
            # -- record 1 ------
        if amount_currency > 0:
            line_vals_list.append({
                'name': account1_d.name,
                'date_maturity': self.date,
                'amount_currency': self.amount,
                'currency_id': self.currency_id.id,
                'balance': amount_grn,
                'account_id': account1_d.id,
            })
        else:
            line_vals_list.append({
                'name': account1_d.name,
                'date_maturity': self.date,
                'balance': amount_grn,
                'account_id': account1_d.id,
            })

        line_vals_list.append({
            'name': account1_с.name,
            'date_maturity': self.date,
            'balance': - amount_grn,
            'account_id': account1_с.id,
        })
        # -- record 2 ------
        line_vals_list.append({
            'name': account2_d.name,
            'date_maturity': self.date,
            'balance': self.bank_commission,
            'account_id': account2_d.id,
        })
        line_vals_list.append({
            'name': account2_с.name,
            'date_maturity': self.date,
            'balance': -self.bank_commission,
            'account_id': account2_с.id,
        })
        # --- record 3 -----
        if self.interbank_and_nbu_difference > 0:
            line_vals_list.append(
                {
                    'name': account3_dp.name,
                    'date_maturity': self.date,
                    'balance': abs(self.interbank_and_nbu_difference * self.amount),
                    'account_id': account3_dp.id,
                }
            )
            line_vals_list.append(
                {
                    'name': account3_cp.name,
                    'date_maturity': self.date,
                    'balance': -abs(self.interbank_and_nbu_difference * self.amount),
                    'account_id': account3_cp.id,
                }
            )
        elif self.interbank_and_nbu_difference < 0:
            line_vals_list.append(
                {
                    'name': account3_dn.name,
                    'date_maturity': self.date,
                    'balance': abs(self.interbank_and_nbu_difference * self.amount),
                    'account_id': account3_dn.id,
                }
            )
            line_vals_list.append(
                {
                    'name': account3_cn.name,
                    'date_maturity': self.date,
                    'balance': -abs(self.interbank_and_nbu_difference * self.amount),
                    'account_id': account3_cn.id,
                },
            )

        if self.payment_type == 'outbound' and self.currency_sell_date and self.currency_sell_date_difference != 0:
            if self.currency_sell_date_difference > 0:
                dt_account = self.company_id.income_currency_exchange_account_id
                kt_account = self.company_id.transit_in_foreign_currency_account_id
            else:
                dt_account = self.company_id.transit_in_foreign_currency_account_id
                kt_account = self.company_id.expense_currency_exchange_account_id

            line_vals_list.append(
                {
                    'name': dt_account.name,
                    'date_maturity': self.currency_sell_date,
                    'balance': -abs(self.currency_sell_date_difference * self.amount),
                    'account_id': dt_account.id,
                }
            )
            line_vals_list.append(
                {
                    'name': kt_account.name,
                    'date_maturity': self.currency_sell_date,
                    'balance': abs(self.currency_sell_date_difference * self.amount),
                    'account_id': kt_account.id,
                }
            )

        return line_vals_list

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        self.ensure_one()
        if self.currency_transactions:
            return self._create_currency_exchange_lines()
        else:
            return super()._prepare_move_line_default_vals()

    def _synchronize_to_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            if pay.currency_transactions:
                line_vals_list = self._create_currency_exchange_lines()
                line_commands = [Command.clear()]
                for line in line_vals_list:
                    line_commands.append(Command.create(line))
                pay.move_id.with_context(skip_invoice_sync=True).write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_commands,
                })
            else:
                super(AccountPayment, pay)._synchronize_to_moves(changed_fields)

    def _synchronize_from_moves(self, changed_fields):
        to_synchronize = self.filtered(lambda rec: not rec.currency_transactions)
        super(AccountPayment, to_synchronize)._synchronize_from_moves(changed_fields)
