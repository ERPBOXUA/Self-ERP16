from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import add, end_of, start_of, float_compare
from odoo.tools.misc import format_date


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    gaap = fields.Boolean(
        string="UA GAAP",
        default=True,
    )
    asset_state = fields.Selection(
        related='asset_id.state',
    )
    asset_type = fields.Selection(
        related='asset_id.asset_type',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        related='asset_id.product_id',
    )
    sell_date = fields.Date(
        string="Sell Date",
    )
    value_re_evaluate = fields.Monetary(
        string="Re-evaluate Amount",
    )

    @api.depends('asset_id')
    def _get_selection_modify_options(self):
        if self.env.context.get('resume_after_pause'):
            return [('resume', _("Resume"))]
        if self.env.context.get('asset_type') in ('sale', 'expense'):
            return [('modify', _("Re-evaluate"))]
        return [
            ('dispose', _("Dispose")),
            ('sell', _("Sell")),
            ('modify', _("Re-evaluate")),
            ('pause', _("Pause")),
        ]

    @api.depends('modify_action')
    def _compute_gain_or_loss(self):
        for record in self:
            if record.asset_id.asset_type != 'purchase':
                super(AssetModify, record)._compute_gain_or_loss()
                continue

            if record.modify_action in ('sell', 'dispose'):
                record.gain_or_loss = 'loss'
            else:
                record.gain_or_loss = 'no'

    @api.depends(
        'account_asset_counterpart_id',
        'loss_account_id',
        'gain_account_id',
        'gain_or_loss',
        'modify_action',
        'date',
        'value_residual',
        'salvage_value',
    )
    def _compute_informational_text(self):
        super()._compute_informational_text()

        for wizard in self:
            if wizard.asset_id.asset_type != 'purchase':
                continue

            if wizard.modify_action == 'dispose':
                if wizard.gain_or_loss == 'gain':
                    account = wizard.gain_account_id.display_name or ''
                    gain_or_loss = _("gain")
                elif wizard.gain_or_loss == 'loss':
                    account = wizard.loss_account_id.display_name or ''
                    gain_or_loss = _("loss")
                else:
                    account = ''
                    gain_or_loss = _("gain/loss")
                wizard.informational_text = _(
                    "A depreciation entry will be posted on %s.<br/> A disposal entry will be posted on the %s account <b>%s</b>.",
                    format_date(self.env, wizard.date),
                    gain_or_loss,
                    account,
                )
            elif wizard.modify_action == 'sell':
                if wizard.gain_or_loss == 'gain':
                    account = wizard.gain_account_id.display_name or ''
                elif wizard.gain_or_loss == 'loss' and wizard.asset_state == 'open':
                    account = wizard.account_asset_counterpart_id.display_name or ''
                elif wizard.gain_or_loss == 'loss':
                    account = wizard.loss_account_id.display_name or ''
                else:
                    account = ''
                wizard.informational_text = _(
                    "A depreciation entry will be posted on and including the date %s.<br/> Asset as held for sale entry will be posted on account <b>%s</b>.",
                    format_date(self.env, wizard.date),
                    account,
                )

    @api.depends('company_id')
    def _compute_accounts(self):
        super()._compute_accounts()

        for record in self:
            if record.asset_id.asset_type != 'purchase' and not record.account_asset_counterpart_id and record.asset_id.account_counterpart_id:
                record.account_asset_counterpart_id = record.asset_id.account_counterpart_id

    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        super()._onchange_invoice_ids()

        if self.asset_id.asset_type == 'purchase':
            self.sell_date = self.invoice_ids and self.invoice_ids.mapped('invoice_date')[0] or None

    @api.onchange('value_re_evaluate')
    def _onchange_value_re_evaluate(self):
        self.value_residual = self.asset_id.value_residual + self.value_re_evaluate

    def modify(self):
        if not self.gaap or self.asset_id.asset_type != 'purchase':
            return super().modify()

        self.asset_id.write({'gaap': self.gaap})

        old_values = {
            'method_number': self.asset_id.method_number,
            'method_period': self.asset_id.method_period,
            'value_residual': self.asset_id.value_residual,
            'salvage_value': self.asset_id.salvage_value,
        }

        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'value_residual': self.value_residual,
            'salvage_value': self.salvage_value,
        }

        if self.env.context.get('resume_after_pause'):
            date_before_pause = (
                max(self.asset_id.depreciation_move_ids, key=lambda x: x.date).date
                if self.asset_id.depreciation_move_ids
                else self.asset_id.acquisition_date
            )
            self.date = end_of(self.date, 'month')
            delta_months = relativedelta(self.date, date_before_pause).months
            paused_prorata_date = add(self.asset_id.prorata_date, months=delta_months)
            number_days = (paused_prorata_date - self.asset_id.prorata_date).days

            # We are removing one day to number days because we don't count the current day
            # i.e. If we pause and resume the same day, there isn't any gap whereas for depreciation
            # purpose it would count as one full day
            if float_compare(number_days, 0, precision_rounding=self.currency_id.rounding) < 0:
                raise UserError(_("You cannot resume at a date equal to or before the pause date"))

            asset_vals.update({'asset_paused_days': number_days})
            asset_vals.update({'state': 'open'})

            self.asset_id.message_post(body=_("Asset unpaused. %s", self.name))

        current_asset_book = self.asset_id.value_residual + self.asset_id.salvage_value
        after_asset_book = self.value_residual + self.salvage_value
        increase = after_asset_book - current_asset_book

        salvage_value = min(self.salvage_value, self.asset_id.salvage_value)
        new_residual = min(current_asset_book - salvage_value, self.value_residual)
        new_salvage = min(current_asset_book - new_residual, self.salvage_value)
        residual_increase = max(0, self.value_residual - new_residual)
        salvage_increase = max(0, self.salvage_value - new_salvage)

        # Check for residual/salvage increase while rounding with the company currency precision to prevent float precision issues.
        if self.currency_id.round(residual_increase + salvage_increase) > 0:
            move = self.env['account.move'].create(
                {
                    'journal_id': self.asset_id.journal_id.id,
                    'date': self.date,
                    'move_type': 'entry',
                    'line_ids': [
                        Command.create(
                            {
                                'account_id': self.asset_id.account_asset_id.id,
                                'debit': residual_increase + salvage_increase,
                                'credit': 0,
                                'name': _("Value increase for: %(asset)s", asset=self.asset_id.name),
                            }
                        ),
                        Command.create(
                            {
                                'account_id': self.account_asset_counterpart_id.id,
                                'debit': 0,
                                'credit': residual_increase + salvage_increase,
                                'name': _("Value increase for: %(asset)s", asset=self.asset_id.name),
                            }
                        ),
                    ],
                }
            )
            move._post()

            if self.modify_action == 'modify':
                draft_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
                    lambda x: x.state == 'draft' and x.date >= (self.date or fields.Date.today())
                )
                if draft_depreciation_move_ids:
                    self.method_number = len(draft_depreciation_move_ids)
            elif self.modify_action == 'resume':
                posted_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
                    lambda r: r.state == 'posted'
                )
                self.method_number -= len(posted_depreciation_move_ids)

            asset_increase = self.env['account.asset'].create(
                {
                    'name': self.asset_id.name + ': ' + self.name if self.name else '',
                    'product_id': self.asset_id.product_id.id,
                    'currency_id': self.asset_id.currency_id.id,
                    'company_id': self.asset_id.company_id.id,
                    'asset_type': self.asset_id.asset_type,
                    'method': self.asset_id.method,
                    'method_number': self.method_number,
                    'method_period': self.method_period,
                    'acquisition_date': self.date,
                    'commissioning_date': self.date,
                    'asset_paused_days': self.asset_id.asset_paused_days,
                    'value_residual': residual_increase,
                    'salvage_value': salvage_increase,
                    'prorata_date': start_of(add(self.date or fields.Date.today(), months=1), 'month'),
                    'prorata_computation_type': self.asset_id.prorata_computation_type,
                    'original_value': residual_increase + salvage_increase,
                    'account_asset_id': self.asset_id.account_asset_id.id,
                    'account_depreciation_id': self.account_depreciation_id.id,
                    'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                    'journal_id': self.asset_id.journal_id.id,
                    'parent_id': self.asset_id.id,
                    'gaap': self.asset_id.gaap,
                    'account_asset_counterpart_id': self.account_asset_counterpart_id.id,
                    'original_move_line_ids': [
                        Command.set(
                            move.line_ids.filtered(lambda r: r.account_id == self.asset_id.account_asset_id).ids
                        ),
                    ],
                }
            )
            asset_increase.validate()

            subject = _("A gross increase has been created: %s", asset_increase._get_html_link())
            self.asset_id.message_post(body=subject)

        if self.modify_action == 'resume' and not self.env.context.get('resume_after_pause'):
            self.asset_id._create_move_before_date(self.date)

        if increase < 0:
            if self.env['account.move'].search(
                [
                    ('asset_id', '=', self.asset_id.id),
                    ('state', '=', 'draft'),
                    ('date', '<=', self.date),
                ]
            ):
                raise UserError(
                    _(
                        "There are unposted depreciations prior to the selected operation date, please deal with them first."
                    )
                )
            move = (
                self.env['account.move']
                .create(
                    self.env['account.move']._prepare_move_for_asset_depreciation(
                        {
                            'amount': -increase,
                            'asset_id': self.asset_id,
                            'move_ref': _("Value decrease for: %(asset)s", asset=self.asset_id.name),
                            'depreciation_beginning_date': self.date,
                            'depreciation_end_date': self.date,
                            'date': self.date,
                            'asset_number_days': 0,
                            'asset_value_change': True,
                        }
                    )
                )
                ._post()
            )

        asset_vals.update(
            {
                'value_residual': new_residual,
                'salvage_value': new_salvage,
            }
        )
        self.asset_id.write(asset_vals)

        self.asset_id.compute_depreciation_board()

        for child in self.asset_id.children_ids:
            child.compute_depreciation_board()
            child._check_depreciations()
            child.depreciation_move_ids.filtered(lambda move: move.state != 'posted')._post()
        tracked_fields = self.env['account.asset'].fields_get(old_values.keys())
        changes, tracking_value_ids = self.asset_id._mail_track(tracked_fields, old_values)
        if changes:
            self.asset_id.message_post(
                body=_("Depreciation board modified %s", self.name),
                tracking_value_ids=tracking_value_ids,
            )
        self.asset_id._check_depreciations()
        self.asset_id.depreciation_move_ids.filtered(lambda move: move.state != 'posted')._post()

        return {'type': 'ir.actions.act_window_close'}

    def pause(self):
        for record in self:
            if record.asset_id.asset_type != 'purchase':
                super(AssetModify, record).pause()
                continue

            if record.gaap != record.asset_id.gaap:
                record.asset_id.write({'gaap': record.gaap})
            record.asset_id.pause(pause_date=record.date, message=self.name)

    def action_held_for_sell(self):
        self.ensure_one()

        self.asset_id.write(
            {
                'state': 'on_hold',
                'account_counterpart_id': self.account_asset_counterpart_id.id,
                'held_on_sell_date': self.date,
                'held_on_sell_name': self.name,
            }
        )
        self.asset_id.set_to_held_on_sell(
            invoice_line_ids=self.invoice_line_ids,
            date=self.date,
            message=self.name,
        )

        return self.asset_id.action_asset_sell()

    def action_sell_later(self):
        self.ensure_one()

        self.asset_id.set_to_on_hold()

    def action_cancel_held_for_sell(self):
        self.ensure_one()

        self.date = fields.Date.today()
        self.asset_id.write({'state': 'open'})
        self.asset_id.message_post(body=_("Cancellation of sale. %s", self.name if self.name else ''))
        self.modify()

    def sell_dispose(self):
        self.ensure_one()

        if not self.gaap or self.asset_id.asset_type != 'purchase':
            return super().sell_dispose()

        if self.modify_action == 'dispose':
            invoice_lines = self.env['account.move.line']

            return self.asset_id.set_to_close(invoice_line_ids=invoice_lines, date=self.date, message=self.name)

        if not self.sell_date or not self.invoice_ids or not self.loss_account_id:
            raise UserError(_("You cannot sell asset without Sell Date, Customer Invoice or Loss Account"))

        self.asset_id.write({'account_sell_id': self.loss_account_id})

        return self.asset_id.sell_asset(
            invoice_ids=self.invoice_ids,
            sell_date=self.sell_date,
            message=self.name,
        )
