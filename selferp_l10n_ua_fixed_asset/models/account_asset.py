from math import copysign

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, add, start_of, end_of, float_is_zero
from odoo.tools.float_utils import float_round


DAYS_PER_MONTH = 30


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    state = fields.Selection(
        selection_add=[('on_hold', "On Hold")],
        ondelete={'on_hold': 'set draft'},
    )
    account_capital_investment_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        string="Capital Investment Account",
        compute='_compute_account_capital_investment_id',
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id), ('account_type', 'in', ('asset_current', 'asset_fixed')), ('is_off_balance', '=', False)]",
        help="Transit account used to record the purchase of the asset before it is used in business activities.",
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        compute='_compute_product_id',
        store=True,
        readonly=False,
        domain="[('detailed_type', '=', 'assets')]",
        copy=False,
    )
    asset_number = fields.Char(
        string="Asset Number",
        copy=False,
    )
    move_asset_on_run_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="Account Move for Asset On Run",
        copy=False,
    )
    transfer_of_assets_balances = fields.Boolean(
        string="Transfer of assets balances",
        default=False,
        copy=False,
        help="Check the box if the initial balances of assets (assets that are already in a depreciation process in your accounting) are imported from another software",
    )
    acquisition_date = fields.Date(
        string="Acquisition Date",
    )
    prorata_date = fields.Date(
        string="Prorata Date",
    )
    commissioning_date = fields.Date(
        string="Commissioning Date",
        compute='_compute_commissioning_date',
        store=True,
        readonly=False,
        copy=False,
    )
    sell_date = fields.Date(
        string="Sell Date",
        copy=False,
    )
    held_on_sell_date = fields.Date(
        string="Held on Sell Date",
        copy=False,
    )
    held_on_sell_name = fields.Char(
        copy=False,
    )
    account_counterpart_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        domain="[('company_id', '=', company_id)]",
        string="Counterpart Account",
    )
    account_sell_id = fields.Many2one(
        comodel_name='account.account',
        ondelete='restrict',
        domain="[('company_id', '=', company_id)]",
        string="Sell Account",
    )
    move_asset_sell_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        string="Account Move for Sell Asset",
        copy=False,
    )
    gaap = fields.Boolean(
        string="UA GAAP",
        default=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]",
        string="Customer Invoices",
        copy=False,
    )
    method = fields.Selection(
        selection_add=[('50/50', "50/50"), ('100', "100%")],
        ondelete={'50/50': 'set linear', '100': 'set linear'},
    )
    re_evaluate_line_ids = fields.One2many(
        comodel_name='account.asset.re_evaluate.line',
        inverse_name='asset_id',
        string="Re-evaluate Lines",
        copy=False,
    )
    account_asset_counterpart_id = fields.Many2one(
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        string="Asset Counterpart Account",
        copy=False,
    )
    equipment_id = fields.Many2one(
        comodel_name='maintenance.equipment',
        string="Equipment",
    )
    depreciation_value = fields.Monetary(
        string="Depreciation Value",
        compute='_compute_depreciation_value',
    )
    amortized_cost = fields.Monetary(
        compute='_compute_amortized_cost',
    )

    @api.depends('acquisition_date')
    def _compute_commissioning_date(self):
        for asset in self:
            if asset.asset_type != 'purchase':
                continue

            asset.commissioning_date = asset.acquisition_date

    @api.depends('original_move_line_ids')
    def _compute_acquisition_date(self):
        for asset in self:
            super(AccountAsset, asset)._compute_acquisition_date()

            if asset.asset_type != 'purchase':
                continue

            asset._compute_commissioning_date()

    @api.depends('account_depreciation_id', 'account_depreciation_expense_id', 'original_move_line_ids')
    def _compute_account_asset_id(self):
        for record in self:
            if record.asset_type != 'purchase':
                super(AccountAsset, record)._compute_account_asset_id()
                continue

            if not record.account_asset_id:
                if record.original_move_line_ids.account_id:
                    if len(record.original_move_line_ids.account_id) > 1:
                        raise UserError(_("All the lines should be from the same account"))
                    record.account_asset_id = record.original_move_line_ids.account_id[0]
                else:
                    record._onchange_account_depreciation_id()

    @api.depends('original_move_line_ids')
    def _compute_account_capital_investment_id(self):
        for asset in self:
            if asset.asset_type != 'purchase':
                continue

            if asset.original_move_line_ids.account_id and not asset.account_capital_investment_id:
                if len(asset.original_move_line_ids.account_id) > 1:
                    raise UserError(_("All the lines should be from the same account"))
                asset.account_capital_investment_id = asset.original_move_line_ids.account_id[0]

    @api.depends('original_move_line_ids')
    def _compute_product_id(self):
        for asset in self:
            if asset.asset_type != 'purchase':
                continue

            if asset.original_move_line_ids.product_id and not asset.product_id:
                if len(asset.original_move_line_ids.product_id) > 1:
                    raise UserError(_("All the lines should be with the same product"))
                asset.product_id = asset.original_move_line_ids.product_id[0]

    @api.depends('depreciation_move_ids.state', 'parent_id', 'move_asset_on_run_id.state', 'move_asset_sell_id.state')
    def _compute_counts(self):
        super()._compute_counts()

        for asset in self:
            if asset.move_asset_on_run_id.state == 'posted':
                asset.depreciation_entries_count += 1
            if asset.move_asset_sell_id.state == 'posted':
                asset.depreciation_entries_count += 1

    @api.depends('commissioning_date')
    def _compute_prorata_date(self):
        for asset in self:
            if asset.asset_type != 'purchase':
                super(AccountAsset, asset)._compute_prorata_date()
                continue

            asset.prorata_date = asset.commissioning_date and start_of(add(asset.commissioning_date, months=1), 'month') or None

    @api.depends('original_move_line_ids')
    def _compute_related_purchase_value(self):
        for asset in self:
            super(AccountAsset, asset)._compute_related_purchase_value()
            if asset.asset_type != 'purchase':
                continue

            if asset.account_asset_id.multiple_assets_per_line:
                asset.related_purchase_value = sum(asset.original_move_line_ids.mapped(lambda r: r.balance / (r.quantity or 1)))

    @api.depends(
        'depreciation_move_ids.state',
        'depreciation_move_ids.depreciation_value',
        'children_ids.depreciation_move_ids.depreciation_value',
    )
    def _compute_depreciation_value(self):
        for asset in self:
            posted_depreciation_moves = asset.depreciation_move_ids.filtered(lambda mv: mv.state == 'posted')
            posted_depreciation_moves += asset.children_ids.depreciation_move_ids.filtered(lambda mv: mv.state == 'posted')
            asset.depreciation_value = sum(posted_depreciation_moves.mapped('depreciation_value'))

    @api.depends(
        'value_residual',
        'children_ids.value_residual',
    )
    def _compute_amortized_cost(self):
        for record in self:
            record.amortized_cost = record.value_residual + sum(record.children_ids.mapped('value_residual'))

    @api.depends('method_number', 'method_period', 'prorata_computation_type')
    def _compute_lifetime_days(self):
        for asset in self:
            if asset.asset_type != 'purchase':
                super(AccountAsset, asset)._compute_lifetime_days()
                continue

            if not asset.gaap:
                super(AccountAsset, asset)._compute_lifetime_days()

            if asset.prorata_computation_type == 'daily_computation':
                asset.asset_lifetime_days = (
                    asset.prorata_date
                    + relativedelta(months=int(asset.method_period) * asset.method_number)
                    - asset.prorata_date
                ).days
            else:
                asset.asset_lifetime_days = int(asset.method_period) * asset.method_number * DAYS_PER_MONTH

    @api.onchange('prorata_computation_type')
    def _onchange_prorata_computation_type(self):
        if self.asset_type == 'purchase' and self.prorata_computation_type == 'none':
            raise UserError(_("This option (No Prorata) is not active for the Ukrainian localisation"))

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.asset_type == 'purchase' and self.model_id:
            self.account_asset_id = self.model_id.account_asset_id

        super()._onchange_model_id()

    @api.onchange('method')
    def _onchange_method(self):
        if self.method == '100':
            self.method_number = 1
            self.method_period = '1'
        elif self.model_id:
            self.method_number = self.model_id.method_number
            self.method_period = self.model_id.method_period

    @api.constrains('prorata_computation_type')
    def _check_prorata_computation_type(self):
        for asset in self:
            if asset.asset_type == 'purchase' and asset.prorata_computation_type == 'none':
                raise UserError(_("This option (No Prorata) is not active for the Ukrainian localisation"))

    @api.constrains('commissioning_date', 'acquisition_date')
    def _check_commissioning_n_acquisition_dates(self):
        for asset in self:
            if asset.state == 'model':
                continue
            if not asset.commissioning_date:
                raise UserError(_("You must fill in Commissioning date"))
            if asset.asset_type == 'purchase' and asset.commissioning_date < asset.acquisition_date:
                raise UserError(_("Commissioning date cannot be earlier than acquisition date"))

    @api.constrains('depreciation_move_ids')
    def _check_depreciations(self):
        for asset in self:
            if asset.asset_type == 'purchase' and asset.method == '50/50':
                continue

            super(AccountAsset, asset)._check_depreciations()

    @api.constrains('re_evaluate_line_ids')
    def _check_re_evaluate_line_ids(self):
        for record in self:
            if (
                record.re_evaluate_line_ids
                and sum(record.re_evaluate_line_ids.mapped('value_re_evaluate')) > record.book_value
            ):
                raise UserError(_("Value Re-evaluate shouldn`t be more than Book Value"))

    def validate(self):
        super().validate()

        for asset in self:
            if asset.asset_type == 'purchase' and not asset.transfer_of_assets_balances and not asset.parent_id:
                asset.move_asset_on_run_id = self.env['account.move'].create(asset._prepare_move_for_asset_on_run())
                asset.move_asset_on_run_id._post()
                asset.message_post(body=_("Move on run. %s", asset.move_asset_on_run_id.name))

    def action_asset_sell(self):
        self.ensure_one()

        new_wizard = self.env['asset.modify'].create(
            {
                'asset_id': self.id,
                'modify_action': 'sell',
                'name': self.held_on_sell_name,
                'date': self.held_on_sell_date,
            }
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sell Asset"),
            'res_model': 'asset.modify',
            'res_id': new_wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_equipment(self):
        self.ensure_one()

        if self.equipment_id:
            raise UserError(_("Equipment already exists"))

        self.equipment_id = self.env['maintenance.equipment'].create(
            {
                'name': self.name,
                'partner_id': self.original_move_line_ids.partner_id
                    and self.original_move_line_ids.partner_id[0].id
                    or None,
                'partner_ref': self.original_move_line_ids and self.original_move_line_ids[0].move_id.name or None,
                'cost': self.original_value,
            }
        )

    def action_show_equipment(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Equipment"),
            'res_model': self.equipment_id._name,
            'res_id': self.equipment_id.id,
            'view_mode': 'form',
        }

    def action_asset_modify(self):
        self.ensure_one()

        if self.asset_type != 'purchase':
            return super().action_asset_modify()

        new_wizard = self.env['asset.modify'].create(
            {
                'asset_id': self.id,
                'modify_action': 'resume'
                    if self.env.context.get('resume_after_pause')
                    else ('dispose' if self.asset_type == 'purchase' else 'modify'),
                'gaap': self.gaap if self.env.context.get('resume_after_pause') else True,
            }
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _("Modify Asset"),
            'res_model': 'asset.modify',
            'res_id': new_wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def open_entries(self):
        if self.asset_type != 'purchase':
            return super().open_entries()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Entries"),
            'res_model': 'account.move',
            'domain': [('id', 'in', (self.depreciation_move_ids + self.move_asset_on_run_id + self.move_asset_sell_id).ids)],
            'view_mode': 'tree,form',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
            'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
            'context': dict(self._context, create=False),
        }

    def set_to_on_hold(self):
        self.write({'state': 'on_hold'})

    def set_to_held_on_sell(self, invoice_line_ids, date, message=None):
        self.ensure_one()

        self._get_disposal_moves([invoice_line_ids], date)
        self.message_post(body=_("Asset held on sell. %s", message if message else ''))

    def sell_asset(self, invoice_ids, sell_date=None, message=None):
        self.ensure_one()

        self.invoice_ids = invoice_ids

        self.sell_date = sell_date or fields.Date.today()

        self.move_asset_sell_id = self.env['account.move'].create(self._prepare_move_for_sell_asset())
        self.move_asset_sell_id._post()

        self.message_post(body=_("Asset sold. %s", message if message else ''))

        self.write({'state': 'close'})

        return {
            'type': 'ir.actions.act_window',
            'name': _("Sell Move"),
            'res_model': 'account.move',
            'res_id': self.move_asset_sell_id.id,
            'view_mode': 'form',
        }

    def set_to_cancelled(self):
        super().set_to_cancelled()

        for asset in self:
            if asset.move_asset_on_run_id:
                asset.move_asset_on_run_id.button_draft()
                asset.move_asset_on_run_id.unlink()
            if asset.move_asset_sell_id:
                asset.move_asset_sell_id.button_draft()
                asset.move_asset_sell_id.unlink()
                asset.sell_date = None

    def _prepare_move_for_asset_on_run(self):
        self.ensure_one()

        analytic_distribution = self.analytic_distribution
        date_on_run = self.commissioning_date
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        prec = company_currency.decimal_places
        amount_currency = self.original_value
        amount = self.original_value
        if current_currency != company_currency:
            amount = current_currency._convert(amount_currency, company_currency, self.company_id, date_on_run)

        positive_amount = float_compare(amount, 0.0, precision_digits=prec) > 0
        move_lines = [
            fields.Command.create(
                {
                    'name': self.name,
                    'account_id': self.account_capital_investment_id.id,
                    'debit': 0.0 if positive_amount else -amount,
                    'credit': amount if positive_amount else 0.0,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                    'product_id': self.product_id.id if positive_amount else None,
                    'amount_currency': -amount_currency,
                }
            ),
            fields.Command.create(
                {
                    'name': self.name,
                    'account_id': self.account_asset_id.id,
                    'debit': amount if positive_amount else 0.0,
                    'credit': 0.0 if positive_amount else -amount,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                    'product_id': None if positive_amount else self.product_id.id,
                    'amount_currency': amount_currency,
                }
            ),
        ]

        return {
            'date': date_on_run,
            'journal_id': self.journal_id.id,
            'ref': _("%s: On Run", self.name),
            'name': '/',
            'move_type': 'entry',
            'currency_id': current_currency.id,
            'line_ids': move_lines,
        }

    def _prepare_move_for_sell_asset(self):
        self.ensure_one()

        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        prec = company_currency.decimal_places

        dep_move_ids = self.depreciation_move_ids.filtered(lambda x: x.depreciation_value).sorted(lambda x: (x.date, x.id))
        amount_currency = dep_move_ids and dep_move_ids[-1].depreciation_value or self.value_residual
        amount = amount_currency
        if current_currency != company_currency:
            amount = current_currency._convert(amount_currency, company_currency, self.company_id, self.sell_date)

        positive_amount = float_compare(amount, 0.0, precision_digits=prec) > 0
        move_lines = [
            fields.Command.create(
                {
                    'name': self.name,
                    'account_id': self.account_sell_id.id,
                    'credit': 0.0 if positive_amount else -amount,
                    'debit': amount if positive_amount else 0.0,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
            ),
            fields.Command.create(
                {
                    'name': self.name,
                    'account_id': self.account_counterpart_id.id,
                    'debit': 0.0 if positive_amount else -amount,
                    'credit': amount if positive_amount else 0.0,
                    'currency_id': current_currency.id,
                    'amount_currency': -amount_currency,
                }
            ),
        ]

        return {
            'date': self.sell_date,
            'journal_id': self.journal_id.id,
            'ref': _("%s: Sell", self.name),
            'name': '/',
            'move_type': 'entry',
            'currency_id': current_currency.id,
            'line_ids': move_lines,
        }

    def _create_move_before_date(self, date):
        """ Cancel all the moves after the given date and replace them by a new one.

            The new depreciation/move is depreciating the residual value.
        """
        if not self.gaap or self.asset_type != 'purchase':
            super()._create_move_before_date(date)
            return

        if self.method == '50/50':
            return

        self._cancel_future_moves(date)

        all_lines_before_date = self.depreciation_move_ids.filtered(lambda x: x.date <= date)
        if all_lines_before_date:
            imported_amount = 0
            amount_total_draft = sum(
                all_lines_before_date.filtered(lambda x: x.state == 'draft').mapped('amount_total')
            )
            value_residual = self.value_residual - amount_total_draft
        else:
            imported_amount = self.already_depreciated_amount_import
            value_residual = self.value_residual + self.already_depreciated_amount_import

        days_already_depreciated = sum(all_lines_before_date.mapped('asset_number_days'))
        start_depreciation_date = add(
            self.paused_prorata_date,
            months=float_round(days_already_depreciated / DAYS_PER_MONTH, precision_digits=0),
        )
        beginning_depreciation_date = start_of(start_depreciation_date, 'month')

        days_left = self.asset_lifetime_days - days_already_depreciated

        days_depreciated, amount = self._compute_board_amount(
            value_residual,
            beginning_depreciation_date,
            end_of(date, 'month'),
            days_already_depreciated,
            days_left,
            value_residual,
        )

        if abs(imported_amount) <= abs(amount):
            amount -= imported_amount
        if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            if self.asset_type == 'sale':
                amount *= -1
            new_line = self._insert_depreciation_line(amount, beginning_depreciation_date, date, days_depreciated)
            new_line._post()

    def _get_disposal_moves(self, invoice_lines_list, disposal_date):
        def _get_line(asset, amount, account):
            return fields.Command.create(
                {
                    'name': asset.name,
                    'account_id': account.id,
                    'balance': -amount,
                    'analytic_distribution': asset.analytic_distribution,
                    'currency_id': asset.currency_id.id,
                    'amount_currency': -asset.company_id.currency_id._convert(
                        from_amount=amount,
                        to_currency=asset.currency_id,
                        company=asset.company_id,
                        date=disposal_date,
                    ),
                },
            )

        if self.asset_type != 'purchase':
            return super()._get_disposal_moves(invoice_lines_list, disposal_date)

        move_ids = []
        for asset, invoice_line_ids in zip(self, invoice_lines_list):
            asset._create_move_before_date(disposal_date)

            dict_invoice = {}
            invoice_amount = 0

            initial_amount = asset.original_value

            # fix get account from account_asset_id, not from asset.original_move_line_ids.account_id
            if asset.gaap or len(asset.original_move_line_ids.account_id) != 1:
                initial_account = asset.account_asset_id
            else:
                initial_account = asset.original_move_line_ids.account_id

            all_lines_before_disposal = asset.depreciation_move_ids.filtered(lambda x: x.date <= disposal_date)
            sum_depreciation_value = sum(all_lines_before_disposal.mapped('depreciation_value'))
            depreciated_amount = asset.currency_id.round(
                copysign(
                    sum_depreciation_value + asset.already_depreciated_amount_import,
                    -initial_amount,
                )
            )
            depreciation_account = asset.account_depreciation_id
            for invoice_line in invoice_line_ids:
                abs_amount = copysign(invoice_line.balance, -initial_amount)
                dict_invoice[invoice_line.account_id] = abs_amount + dict_invoice.get(invoice_line.account_id, 0)
                invoice_amount += abs_amount
            list_accounts = [(amount, account) for account, amount in dict_invoice.items()]
            difference = -initial_amount - depreciated_amount - invoice_amount

            if asset.gaap and asset.state == 'on_hold':
                loss_account = asset.account_counterpart_id
                asset_name = asset.name + ': ' + _("Sale")
            else:
                loss_account = asset.company_id.loss_account_id
                asset_name = asset.name + ': ' + (_("Disposal") if not invoice_line_ids else _("Sale"))

            difference_account = asset.company_id.gain_account_id if difference > 0 else loss_account
            line_datas = (
                [(initial_amount, initial_account), (depreciated_amount, depreciation_account)]
                + list_accounts
                + [(difference, difference_account)]
            )
            vals = {
                'asset_id': asset.id,
                'ref': asset_name,
                'asset_depreciation_beginning_date': disposal_date,
                'date': disposal_date,
                'journal_id': asset.journal_id.id,
                'move_type': 'entry',
                'line_ids': [_get_line(asset, amount, account) for amount, account in line_datas if account],
            }
            asset.write({'depreciation_move_ids': [fields.Command.create(vals)]})
            move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        if move_ids:
            self.depreciation_move_ids.filtered(lambda m: m.state == 'draft')._post()

        return move_ids

    def _cancel_future_moves(self, date):
        """ Cancel all the depreciation entries after the date given as parameter.

            When possible, it will reset those to draft before unlinking them, reverse them otherwise.

            :param date: date after which the moves are deleted/reversed
        """
        if not self.gaap or self.asset_type != 'purchase':
            super()._cancel_future_moves(date)
            return

        to_reverse = self.env['account.move']
        to_cancel = self.env['account.move']
        for asset in self:
            posted_moves = asset.depreciation_move_ids.filtered(
                lambda m: (not m.reversal_move_id and not m.reversed_entry_id and m.state == 'posted' and m.date > date)
            )
            lock_date = asset.company_id._get_user_fiscal_lock_date()
            for move in posted_moves:
                if move.inalterable_hash or move.date <= lock_date:
                    to_reverse += move
                else:
                    to_cancel += move
        to_reverse._reverse_moves(cancel=True)
        to_cancel.button_draft()
        # fix filter by date
        self.depreciation_move_ids.filtered(lambda m: m.state == 'draft' and m.date > date).unlink()

    def calc_remaining_period(self, from_date=None):
        self.ensure_one()

        return len(self.depreciation_move_ids.filtered(
            lambda x: x.state == 'draft' and x.date >= (from_date or fields.Date.today())
        ))

    def _compute_board_amount(
        self,
        residual_amount,
        period_start_date,
        period_end_date,
        days_already_depreciated,
        days_left_to_depreciated,
        residual_declining,
    ):
        if not self.gaap or self.asset_type != 'purchase':
            return super()._compute_board_amount(
                residual_amount,
                period_start_date,
                period_end_date,
                days_already_depreciated,
                days_left_to_depreciated,
                residual_declining,
            )

        if self.asset_lifetime_days == 0:
            return 0, 0

        number_days = self._get_delta_days(period_start_date, period_end_date)
        total_days = number_days + days_already_depreciated

        if days_left_to_depreciated <= 0:
            computed_linear_amount = residual_amount
        else:
            computed_linear_amount = residual_amount * number_days / days_left_to_depreciated
        if float_compare(residual_amount, 0, precision_rounding=self.currency_id.rounding) >= 0:
            linear_amount = min(computed_linear_amount, residual_amount)
            amount = max(linear_amount, 0)
        else:
            linear_amount = max(computed_linear_amount, residual_amount)
            amount = min(linear_amount, 0)

        if abs(residual_amount) < abs(amount) or total_days >= self.asset_lifetime_days:
            # If the residual amount is less than the computed amount, we keep the residual amount
            # If total_days is greater or equals to asset lifetime days, it should mean that
            # the asset will finish in this period and the value for this period is equals to the residual amount.
            amount = residual_amount

        return number_days, self.currency_id.round(amount)

    def compute_depreciation_board(self, date=False):
        self.ensure_one()

        if not self.gaap or self.asset_type != 'purchase':
            super().compute_depreciation_board(date)
            return

        new_depreciation_moves_data = self._recompute_board(date)

        # Need to unlink draft move before adding new one because if we create new move before, it will cause an error
        # in the compute for the depreciable/cumulative value
        if not self.env.context.get('resume_after_pause'):
            self.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').unlink()

        new_depreciation_moves = self.env['account.move'].create(new_depreciation_moves_data)
        if self.state == 'open':
            # In case of the asset is in running mode, we post in the past and set to auto post move in the future
            new_depreciation_moves._post()

    def _get_depreciation_move_values_50_50(self):
        self.ensure_one()

        depreciation_move_values = []
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == 'posted' and not mv.asset_value_change
        ).sorted(key=lambda mv: (mv.date, mv.id))
        if posted_depreciation_move_ids:
            return depreciation_move_values

        period_end_depreciation_date = self._get_end_period_date(self.prorata_date)
        depreciation_move_values.append(
            self.env['account.move']._prepare_move_for_asset_depreciation(
                {
                    'amount': self.value_residual / 2,
                    'asset_id': self,
                    'depreciation_beginning_date': self.prorata_date,
                    'date': period_end_depreciation_date,
                    'asset_number_days': self._get_delta_days(self.prorata_date, period_end_depreciation_date),
                }
            )
        )

        return depreciation_move_values

    def _recompute_board(self, start_depreciation_date=False):
        self.ensure_one()

        if self.method == '50/50':
            return self._get_depreciation_move_values_50_50()

        if not self.gaap or self.asset_type != 'purchase':
            return super()._recompute_board(start_depreciation_date)

        residual_amount = self.value_residual

        # All depreciation moves that are posted
        if self.env.context.get('resume_after_pause'):
            posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
                lambda mv: not mv.asset_value_change
            ).sorted(key=lambda mv: (mv.date, mv.id))
            residual_amount -= sum(
                self.depreciation_move_ids.filtered(lambda x: x.state == 'draft').mapped('amount_total')
            )
        else:
            posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
                lambda mv: mv.state == 'posted' and not mv.asset_value_change
            ).sorted(key=lambda mv: (mv.date, mv.id))

        imported_amount = self.already_depreciated_amount_import
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_amount

        # Days already depreciated and paused
        days_already_depreciated = sum(posted_depreciation_move_ids.mapped('asset_number_days'))
        # fix without extra days
        start_depreciation_date = add(
            self.paused_prorata_date,
            months=float_round(days_already_depreciated / DAYS_PER_MONTH, precision_digits=0),
        )
        start_depreciation_date = start_of(start_depreciation_date, 'month')

        days_left_to_depreciated = self.asset_lifetime_days - days_already_depreciated

        depreciation_move_values = []
        while days_already_depreciated < self.asset_lifetime_days:
            period_end_depreciation_date = self._get_end_period_date(start_depreciation_date)

            days, amount = self._compute_board_amount(
                residual_amount,
                start_depreciation_date,
                period_end_depreciation_date,
                days_already_depreciated,
                days_left_to_depreciated,
                residual_declining,
            )
            residual_amount -= amount

            if not posted_depreciation_move_ids:
                if abs(imported_amount) <= abs(amount):
                    amount -= imported_amount
                    imported_amount = 0
                else:
                    imported_amount -= amount
                    amount = 0

            if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                if self.asset_type == 'sale':
                    amount *= -1
                depreciation_move_values.append(
                    self.env['account.move']._prepare_move_for_asset_depreciation(
                        {
                            'amount': amount,
                            'asset_id': self,
                            'depreciation_beginning_date': start_depreciation_date,
                            'date': period_end_depreciation_date,
                            'asset_number_days': days,
                        }
                    )
                )
            days_already_depreciated += days

            days_left_to_depreciated = self.asset_lifetime_days - days_already_depreciated
            residual_declining = residual_amount

            start_depreciation_date = period_end_depreciation_date + relativedelta(days=1)

        return depreciation_move_values
