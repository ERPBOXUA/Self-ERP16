from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools import add, start_of, end_of

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAccountAssetModify(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.today = fields.Date.today()
        cls.start_date = start_of(add(cls.today, months=-6), 'month')
        cls.today_1 = add(cls.today, months=1)
        cls.today_2 = add(cls.today, months=2)
        cls.today_3 = add(cls.today, months=3)
        cls.end_month = end_of(cls.today, 'month')
        cls.end_month_1 = end_of(cls.today_1, 'month')
        cls.end_month_2 = end_of(cls.today_2, 'month')
        cls.end_month_3 = end_of(cls.today_3, 'month')

        account_account = cls.env['account.account']
        company_id = cls.company_data['company'].id
        cls.account_capital_investment = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '151000'),
            ],
            limit=1,
        )
        cls.account_asset = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '100000'),
            ],
            limit=1,
        )
        cls.account_depreciation = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '131000'),
            ],
            limit=1,
        )
        cls.account_depreciation.write({'account_type': 'asset_fixed'})
        cls.account_depreciation_expense = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '920000'),
            ],
            limit=1,
        )
        cls.account_dispose = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '976000'),
            ],
            limit=1,
        )
        cls.account_held_on_sell = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '930000'),
            ],
            limit=1,
        )
        cls.account_asset_counterpart = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '286000'),
            ],
            limit=1,
        )
        cls.account_sell = account_account.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '943000'),
            ],
            limit=1,
        )

        cls.product_bike = cls.env['product.product'].create(
            {
                'name': 'bike',
                'detailed_type': 'assets',
                'property_account_expense_id': cls.account_capital_investment.id,
            }
        )

        cls.asset_modify_invoice = cls.init_invoice(
            move_type='out_invoice', invoice_date=cls.today, post=True, products=cls.product_bike
        )

        cls.bill_entry = cls.env['account.move'].create(
            {
                'date': cls.start_date,
                'ref': 'Bike Bill',
                'line_ids': [
                    fields.Command.create(
                        {
                            'account_id': cls.account_capital_investment.id,
                            'product_id': cls.product_bike.id,
                            'debit': 10000,
                            'name': 'Bike',
                        }
                    ),
                    fields.Command.create(
                        {
                            'account_id': cls.company_data['default_account_expense'].id,
                            'product_id': cls.product_bike.id,
                            'credit': 10000,
                            'name': 'Bike',
                        }
                    ),
                    fields.Command.create(
                        {
                            'account_id': cls.account_capital_investment.id,
                            'product_id': cls.product_bike.id,
                            'debit': 5000,
                            'name': 'Bike',
                        }
                    ),
                    fields.Command.create(
                        {
                            'account_id': cls.company_data['default_account_expense'].id,
                            'product_id': cls.product_bike.id,
                            'credit': 5000,
                            'name': 'Bike',
                        }
                    ),
                ],
            }
        )
        cls.bill_entry.action_post()

        cls.bill_in_invoice = cls.env['account.move'].create(
            {
                'date': cls.start_date,
                'ref': 'Bike Bill',
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': cls.start_date,
                'invoice_line_ids': [
                    fields.Command.create(
                        {
                            'account_id': cls.account_capital_investment.id,
                            'product_id': cls.product_bike.id,
                            'name': 'bike',
                            'price_unit': 10000.0,
                            'quantity': 1,
                        }
                    ),
                ],
            }
        )
        cls.bill_in_invoice.action_post()

        cls.model_bike = cls.env['account.asset'].create(
            {
                'account_depreciation_id': cls.account_depreciation.id,
                'account_depreciation_expense_id': cls.account_depreciation_expense.id,
                'account_asset_id': cls.account_asset.id,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'name': 'Big Car - 6 months',
                'method_number': 10,
                'method_period': '1',
                'state': 'model',
            }
        )

        cls.bike = cls.env['account.asset'].create(
            {
                'product_id': cls.product_bike.id,
                'account_capital_investment_id': cls.account_capital_investment.id,
                'account_asset_id': cls.account_asset.id,
                'account_depreciation_id': cls.account_depreciation.id,
                'account_depreciation_expense_id': cls.account_depreciation_expense.id,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'bike',
                'acquisition_date': cls.start_date,
                'commissioning_date': cls.start_date,
                'original_value': 10000,
                'method_number': 10,
                'method_period': '1',
                'method': 'linear',
            }
        )
        cls.bike.validate()

        cls.asset_50_50 = cls.env['account.asset'].create({
            'account_capital_investment_id': cls.account_capital_investment.id,
            'account_asset_id': cls.account_asset.id,
            'account_depreciation_id': cls.account_depreciation.id,
            'account_depreciation_expense_id': cls.account_depreciation_expense.id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'asset_type': 'purchase',
            'name': 'bike 50/50',
            'acquisition_date': cls.start_date,
            'commissioning_date': cls.start_date,
            'original_value': 10000,
            'method_number': 10,
            'method_period': '1',
            'method': '50/50',
        })
        cls.asset_50_50.validate()

        cls.asset_100 = cls.env['account.asset'].create({
            'account_capital_investment_id': cls.account_capital_investment.id,
            'account_asset_id': cls.account_asset.id,
            'account_depreciation_id': cls.account_depreciation.id,
            'account_depreciation_expense_id': cls.account_depreciation_expense.id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'asset_type': 'purchase',
            'name': 'bike 50/50',
            'acquisition_date': cls.start_date,
            'commissioning_date': cls.start_date,
            'original_value': 10000,
            'method_number': 10,
            'method_period': '1',
            'method': 'linear',
        })
        cls.asset_100.method = '100'
        cls.asset_100._onchange_method()
        cls.asset_100.validate()

    @staticmethod
    def _get_record_val_move_line(account_id, credit=0, debit=0):
        return {'credit': credit, 'debit': debit, 'account_id': account_id}

    @staticmethod
    def _get_record_val_depreciation_move(date, amount_total):
        return {'date': date, 'amount_total': amount_total}

    def _check_depreciation_moves(self, depreciation_moves, state, rec_vals, depreciation_move=True):
        moves = depreciation_moves.filtered(lambda x: x.state == state).sorted(key=lambda mv: (mv.date, mv.id))
        if (depreciation_move
            and state == 'draft'
            and self.today == self.end_month
            and rec_vals[0]['date'] == self.end_month
        ):
            rec_vals.pop(0)
        self.assertEqual(len(moves), len(rec_vals))
        self.assertRecordValues(moves, rec_vals)

    def _check_depreciation_move_last_line(self, depreciation_moves, state, rec_vals):
        moves = depreciation_moves.filtered(lambda x: x.state == state).sorted(key=lambda mv: (mv.date, mv.id))
        self._check_moves_lines(moves[-1], rec_vals)

    def _check_initial_posted_depreciation_moves_n_last_lines(self):
        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
        ]
        if self.today == self.end_month:
            rec_vals.append(self._get_record_val_depreciation_move(self.today, 1000))

        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.account_depreciation.id, credit=1000),
            self._get_record_val_move_line(self.account_depreciation_expense.id, debit=1000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'posted', rec_vals)

    def _check_initial_draft_depreciation_moves(self):
        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def _check_moves_lines(self, moves, rec_vals):
        line_ids = moves.line_ids.sorted(key=lambda mv: (mv.date, mv.id))
        self.assertEqual(len(line_ids), len(rec_vals))
        self.assertRecordValues(line_ids, rec_vals)

    def test_asset_on_run(self):
        self.assertEqual(self.bike.name, 'bike')
        self.assertEqual(self.bike.prorata_date, start_of(add(self.bike.commissioning_date, months=1), 'month'))
        self.assertEqual(self.bike.product_id, self.product_bike)
        self.assertEqual(self.bike.move_asset_on_run_id.date, self.start_date)
        self.assertEqual(self.bike.move_asset_on_run_id.state, 'posted')

        rec_vals = [
            self._get_record_val_move_line(self.account_capital_investment.id, credit=10000),
            self._get_record_val_move_line(self.account_asset.id, debit=10000),
        ]
        self._check_moves_lines(self.bike.move_asset_on_run_id, rec_vals)

        rec_vals = [
            {'product_id': self.bike.product_id.id, 'credit': 10000, 'debit': 0},
            {'product_id': None, 'credit': 0, 'debit': 10000},
        ]
        line_ids = self.bike.move_asset_on_run_id.line_ids.sorted(key=lambda mv: (mv.date, mv.id))
        self.assertRecordValues(line_ids, rec_vals)

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

    def test_auto_create_asset(self):
        self.account_capital_investment.write({'create_asset': 'draft'})
        self.assertEqual(self.account_capital_investment.create_asset, 'draft')

        bike_kellys = self.env['product.product'].create(
            {
                'name': 'Kellys',
                'detailed_type': 'assets',
                'property_account_expense_id': self.account_capital_investment.id,
            }
        )
        self.assertEqual(bike_kellys.detailed_type, 'assets')

        bike_azimut = self.env['product.product'].create(
            {
                'name': 'Azimut',
                'property_account_expense_id': self.account_capital_investment.id,
            }
        )
        self.assertNotEqual(bike_azimut.detailed_type, 'assets')

        bill_kellys = self.env['account.move'].create(
            {
                'ref': 'Bill Kellys Azimut',
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': self.start_date,
                'invoice_line_ids': [
                    fields.Command.create(
                        {
                            'account_id': self.account_capital_investment.id,
                            'product_id': bike_kellys.id,
                            'name': 'bike',
                            'price_unit': 10000.0,
                            'quantity': 1,
                        }
                    ),
                    fields.Command.create(
                        {
                            'account_id': self.account_capital_investment.id,
                            'product_id': bike_azimut.id,
                            'name': 'bike',
                            'price_unit': 5000.0,
                            'quantity': 1,
                        }
                    ),
                ],
            }
        )
        bill_kellys.action_post()

        self.assertEqual(len(bill_kellys.asset_ids), 1)
        asset = bill_kellys.asset_ids[0]

        self.assertEqual(asset.product_id, bike_kellys)

    def test_asset_transfer_of_assets_balances(self):
        bike = self.env['account.asset'].create(
            {
                'product_id': self.product_bike.id,
                'account_capital_investment_id': self.account_capital_investment.id,
                'account_asset_id': self.account_asset.id,
                'account_depreciation_id': self.account_depreciation.id,
                'account_depreciation_expense_id': self.account_depreciation_expense.id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'bike',
                'acquisition_date': self.start_date,
                'commissioning_date': self.start_date,
                'original_value': 10000,
                'method_number': 10,
                'method_period': '1',
                'method': 'linear',
                'transfer_of_assets_balances': True,
            }
        )
        bike.validate()

        self.assertFalse(bike.move_asset_on_run_id)

    def test_cancel_asset(self):
        self.bike.set_to_cancelled()

        self.assertEqual(self.bike.state, 'cancelled')
        self.assertFalse(self.bike.move_asset_on_run_id)
        self.assertFalse(self.bike.move_asset_sell_id)
        self.assertFalse(self.bike.sell_date)

    def test_asset_onchange_model(self):
        bike = self.env['account.asset'].create(
            {
                'product_id': self.product_bike.id,
                'model_id': self.model_bike.id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'bike',
                'acquisition_date': self.start_date,
                'commissioning_date': self.start_date,
                'original_value': 10000,
                'method_number': 10,
                'method_period': '1',
                'method': 'linear',
            }
        )

        self.assertEqual(bike.method_number, 10)
        self.assertFalse(bike.account_capital_investment_id)

        bike._onchange_model_id()

        self.assertRecordValues(
            bike,
            [
                {
                    'method_number': 10,
                    'account_asset_id': self.account_asset.id,
                    'account_depreciation_id': self.account_depreciation.id,
                    'account_depreciation_expense_id': self.account_depreciation_expense.id,
                }
            ],
        )

    def test_calc_remaining_period(self):
        if self.today == self.end_month:
            self.assertEqual(self.bike.calc_remaining_period(), 4)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month), 4)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month_1), 4)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month_2), 3)
        else:
            self.assertEqual(self.bike.calc_remaining_period(), 5)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month), 5)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month_1), 4)
            self.assertEqual(self.bike.calc_remaining_period(self.end_month_2), 3)

    def test_asset_copy(self):
        self.assertTrue(self.bike.move_asset_on_run_id)
        self.assertFalse(self.bike.move_asset_sell_id)

        copy_bike = self.bike.copy()
        self.assertFalse(copy_bike.move_asset_on_run_id)
        self.assertFalse(copy_bike.move_asset_sell_id)

    def test_asset_sell_copy(self):
        invoice = self.init_invoice(move_type='out_invoice', post=True, products=self.product_bike)

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify.loss_account_id = self.account_sell
        asset_modify.invoice_ids = invoice.ids
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_date = invoice.invoice_date
        asset_modify.sell_dispose()

        self.assertTrue(self.bike.move_asset_on_run_id)
        self.assertTrue(self.bike.move_asset_sell_id)
        self.assertTrue(self.bike.invoice_ids)

        copy_bike = self.bike.copy()
        self.assertFalse(copy_bike.move_asset_on_run_id)
        self.assertFalse(copy_bike.move_asset_sell_id)
        self.assertFalse(copy_bike.invoice_ids)

    def test_asset_compute_counts_with_run(self):
        posted_entries = self.bike.depreciation_move_ids.filtered(lambda r: r.state == 'posted')
        count_posted_entries = 6 if self.today == self.end_month else 5
        self.assertEqual(len(posted_entries), count_posted_entries)
        self.assertEqual(self.bike.depreciation_entries_count, count_posted_entries + 1)

    def test_model_compute_account_asset_id(self):
        model_bike = self.env['account.asset'].create(
            {
                'name': 'Big Car - 6 months',
                'state': 'model',
            }
        )
        self.assertFalse(model_bike.account_depreciation_id)

        model_bike.write({'account_depreciation_id': self.account_depreciation.id})

        self.assertFalse(model_bike.account_asset_id)
        self.assertEqual(model_bike.account_depreciation_id, self.account_depreciation)

    def test_asset_form_model(self):
        asset_form = Form(self.env['account.asset'].with_context(default_state='model'))
        asset_form.name = "Bike Model"
        asset_form.account_depreciation_id = self.account_depreciation
        asset_form.account_depreciation_expense_id = self.account_depreciation_expense
        asset = asset_form.save()

        self.assertEqual(asset.name, 'Bike Model')

    def test_asset_form_move_line(self):
        move_line_ids = self.bill_in_invoice.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_capital_investment
        )

        asset_form = Form(self.env['account.asset'].with_context(default_asset_type='purchase'))

        asset_form.original_value = 1000

        asset_form.original_move_line_ids.add(move_line_ids)

        self.assertEqual(asset_form.product_id, self.product_bike)
        self.assertEqual(asset_form.account_asset_id, self.account_capital_investment)
        self.assertEqual(asset_form.account_capital_investment_id, self.account_capital_investment)
        self.assertEqual(asset_form.account_depreciation_id, self.account_capital_investment)
        self.assertEqual(asset_form.original_value, 10000)

        asset_form.model_id = self.model_bike

        asset_form.commissioning_date = self.start_date

        asset = asset_form.save()
        self.assertEqual(asset.account_asset_id, self.account_asset)
        self.assertEqual(asset.account_capital_investment_id, self.account_capital_investment)
        self.assertEqual(asset.account_depreciation_id, self.account_depreciation)
        self.assertEqual(asset.account_depreciation_expense_id, self.account_depreciation_expense)

    def test_asset_form_move_line_2(self):
        move_line_ids = self.bill_entry.mapped('line_ids').filtered(lambda x: x.debit)

        asset_form = Form(self.env['account.asset'].with_context(default_asset_type='purchase'))

        asset_form.original_move_line_ids.add(move_line_ids[0])
        self.assertEqual(asset_form.original_value, 10000)

        asset_form.original_move_line_ids.add(move_line_ids[1])
        self.assertEqual(asset_form.original_value, 15000)

        asset_form.model_id = self.model_bike

        self.assertEqual(asset_form.account_asset_id, self.account_asset)
        self.assertEqual(asset_form.account_capital_investment_id, self.account_capital_investment)

        asset = asset_form.save()
        self.assertEqual(asset.account_asset_id, self.account_asset)
        self.assertEqual(asset.account_capital_investment_id, self.account_capital_investment)
        self.assertEqual(asset.account_depreciation_id, self.account_depreciation)
        self.assertEqual(asset.account_depreciation_expense_id, self.account_depreciation_expense)
        self.assertEqual(asset.prorata_date, add(self.start_date, months=1))

    def test_asset_form_move_line_3(self):
        move_line_ids = self.bill_entry.mapped('line_ids').filtered(lambda x: x.debit)

        asset_form = Form(self.env['account.asset'].with_context(default_asset_type='purchase'))

        asset_form.original_move_line_ids.add(move_line_ids[0])
        self.assertEqual(asset_form.original_value, 10000)

        asset_form.original_move_line_ids.add(move_line_ids[1])
        self.assertEqual(asset_form.original_value, 15000)

        self.account_capital_investment.write({'create_asset': 'draft', 'multiple_assets_per_line': True})

        bill_entry = self.env['account.move'].create(
            {
                'line_ids': [
                    fields.Command.create(
                        {
                            'account_id': self.account_capital_investment.id,
                            'product_id': self.product_bike.id,
                            'quantity': 5,
                            'debit': 10000,
                            'name': 'Bike',
                        }
                    ),
                    fields.Command.create(
                        {
                            'account_id': self.company_data['default_account_expense'].id,
                            'product_id': self.product_bike.id,
                            'quantity': 5,
                            'credit': 10000,
                            'name': 'Bike',
                        }
                    ),
                ],
            }
        )
        bill_entry.action_post()
        move_line_ids = bill_entry.mapped('line_ids').filtered(lambda x: x.debit)

        asset_form.original_move_line_ids.add(move_line_ids[0])
        self.assertEqual(asset_form.original_value, 17000)

    def _check_0_posted_depreciation_moves(self):
        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
            self._get_record_val_depreciation_move(self.today, 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_modify_dispose_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'dispose',
                'loss_account_id': self.account_dispose,
            }
        )
        asset_modify.sell_dispose()

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
            self._get_record_val_depreciation_move(self.today, 1000),
            self._get_record_val_depreciation_move(self.today, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=6000),
            self._get_record_val_move_line(self.account_dispose.id, debit=4000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_modify_dispose_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'dispose',
                'loss_account_id': self.account_dispose,
                'date': self.today_1,
            }
        )
        asset_modify.sell_dispose()

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.today_1, 1000),
            self._get_record_val_depreciation_move(self.today_1, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)
        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=7000),
            self._get_record_val_move_line(self.account_dispose.id, debit=3000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_dispose_2(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'dispose',
                'loss_account_id': self.account_dispose,
                'date': self.today_2,
            }
        )
        asset_modify.sell_dispose()

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
            self._get_record_val_depreciation_move(self.today_2, 1000),
            self._get_record_val_depreciation_move(self.today_2, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)
        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=8000),
            self._get_record_val_move_line(self.account_dispose.id, debit=2000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_form_held_for_sell(self):
        asset_modify_form = Form(
            self.env['asset.modify'].with_context(default_asset_id=self.bike.id, default_modify_action='sell')
        )
        self.assertFalse(asset_modify_form.invoice_ids)
        self.assertFalse(asset_modify_form.invoice_line_ids)
        self.assertFalse(asset_modify_form.account_asset_counterpart_id)
        self.assertEqual(asset_modify_form.asset_state, 'open')
        try:
            asset_modify_form.save()
            self.fail("account_asset_counterpart_id is a required field")
        except AssertionError:
            pass

        asset_modify_form.account_asset_counterpart_id = self.account_asset_counterpart
        asset = asset_modify_form.save()
        asset.action_held_for_sell()

    def test_asset_modify_held_on_sell_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'name': 'Held on sell bike',
            }
        )
        asset_modify.action_held_for_sell()

        self.assertEqual(self.bike.account_counterpart_id, self.account_asset_counterpart)
        self.assertEqual(self.bike.held_on_sell_date, self.today)
        self.assertEqual(self.bike.held_on_sell_name, 'Held on sell bike')

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
            self._get_record_val_depreciation_move(self.today, 1000),
            self._get_record_val_depreciation_move(self.today, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=6000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, debit=4000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_modify_held_on_sell_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_1,
                'name': 'Held on sell bike',
            }
        )
        asset_modify.action_held_for_sell()

        self.assertEqual(self.bike.held_on_sell_date, self.today_1)
        self.assertEqual(self.bike.held_on_sell_name, 'Held on sell bike')

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.today_1, 1000),
            self._get_record_val_depreciation_move(self.today_1, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)
        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=7000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, debit=3000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_held_on_sell_2(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_2,
            }
        )
        asset_modify.action_held_for_sell()

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
            self._get_record_val_depreciation_move(self.today_2, 1000),
            self._get_record_val_depreciation_move(self.today_2, 10000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)
        rec_vals = [
            self._get_record_val_move_line(self.bike.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.bike.account_depreciation_id.id, debit=8000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, debit=2000),
        ]
        self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_form_available_fields_after_held_on_sell(self):
        asset_modify_form = Form(
            self.env['asset.modify'].with_context(default_asset_id=self.bike.id, default_modify_action='sell')
        )
        asset_modify_form.account_asset_counterpart_id = self.account_asset_counterpart
        try:
            asset_modify_form.sell_date = self.today
            self.fail("can't write on invisible field sell_date")
        except AssertionError:
            pass

        asset = asset_modify_form.save()
        asset.action_held_for_sell()

        asset_modify_form = Form(
            self.env['asset.modify'].with_context(
                default_asset_id=self.bike.id,
                default_modify_action='sell',
                default_account_asset_counterpart_id=self.account_asset_counterpart.id,
            )
        )
        self.assertTrue(asset_modify_form.gaap)

        asset_modify_form.sell_date = self.today
        try:
            asset_modify_form.gaap = False
            self.fail("can't write on readonly field gaap")
        except AssertionError:
            pass
        try:
            asset_modify_form.date = self.today
            self.fail("can't write on readonly field date")
        except AssertionError:
            pass
        try:
            asset_modify_form.account_asset_counterpart_id = self.account_asset_counterpart
            self.fail("can't write on readonly field account_asset_counterpart_id")
        except AssertionError:
            pass

        asset_modify_form.loss_account_id = self.account_sell

        asset = asset_modify_form.save()

        invoice_1k = self.init_invoice(move_type='out_invoice', post=True, amounts=[1000])
        asset_modify_form.invoice_ids.add(invoice_1k)
        self.assertEqual(asset_modify_form.sell_date, invoice_1k.invoice_date)
        self.assertEqual(asset_modify_form.gain_or_loss, 'loss')

        invoice_10k = self.init_invoice(move_type='out_invoice', post=True, amounts=[20000])
        asset_modify_form.invoice_ids.add(invoice_10k)
        self.assertEqual(asset_modify_form.sell_date, invoice_1k.invoice_date)
        self.assertEqual(asset_modify_form.gain_or_loss, 'loss')

    def test_asset_modify_sell_after_held_on_sell_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify_invoice = self.init_invoice(
            move_type='out_invoice',
            invoice_date=self.today,
            post=True,
            amounts=[1000],
        )
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        self.assertEqual(self.bike.state, 'close')
        self.assertEqual(self.bike.sell_date, self.today)
        self.assertEqual(self.bike.account_sell_id, self.account_sell)
        self.assertEqual(self.bike.invoice_ids, asset_modify_invoice)
        self.assertEqual(self.bike.move_asset_sell_id.date, self.today)

        rec_vals = [
            self._get_record_val_move_line(self.account_sell.id, debit=4000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=4000),
        ]
        self._check_moves_lines(self.bike.move_asset_sell_id, rec_vals)

        self.bike.set_to_cancelled()
        self.assertEqual(self.bike.state, 'cancelled')
        self.assertFalse(self.bike.move_asset_sell_id)

    def test_asset_modify_sell_after_held_on_sell_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_1,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify_invoice = self.init_invoice(
            move_type='out_invoice',
            invoice_date=self.today_1,
            post=True,
            amounts=[1000],
        )
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        self.assertEqual(self.bike.sell_date, self.today_1)
        self.assertEqual(self.bike.invoice_ids, asset_modify_invoice)
        self.assertEqual(self.bike.move_asset_sell_id.date, self.today_1)

        rec_vals = [
            self._get_record_val_move_line(self.account_sell.id, debit=3000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=3000),
        ]
        self._check_moves_lines(self.bike.move_asset_sell_id, rec_vals)

    def test_asset_modify_sell_after_held_on_sell_2(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_2,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify_invoice = self.init_invoice(
            move_type='out_invoice',
            invoice_date=self.today_2,
            post=True,
            amounts=[1000],
        )
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        self.assertEqual(self.bike.sell_date, self.today_2)
        self.assertEqual(self.bike.invoice_ids, asset_modify_invoice)
        self.assertEqual(self.bike.move_asset_sell_id.date, self.today_2)

        rec_vals = [
            self._get_record_val_move_line(self.account_sell.id, debit=2000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=2000),
        ]
        self._check_moves_lines(self.bike.move_asset_sell_id, rec_vals)

    def test_asset_compute_counts_with_sell(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [self.asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        posted_entries = self.bike.depreciation_move_ids.filtered(lambda r: r.state == 'posted')
        self.assertEqual(len(posted_entries), 7)
        self.assertEqual(self.bike.depreciation_entries_count, 9)

    def test_asset_modify_form_sell_later_after_held_on_sell(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
            }
        )
        asset_modify.action_sell_later()

        self.assertEqual(self.bike.state, 'on_hold')

    def test_asset_modify_re_evaluate_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
            }
        )
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 0)

    def test_asset_modify_re_evaluate_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'date': self.today_1,
            }
        )
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 0)

    def test_asset_modify_re_evaluate_increase_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_re_evaluate = 1000
        asset_modify._onchange_value_re_evaluate()
        # asset_modify.value_residual = 6000
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 1)

        asset_increase = self.bike.children_ids[0]

        self.assertEqual(asset_increase.product_id, self.bike.product_id)
        self.assertEqual(asset_increase.acquisition_date, self.today)
        self.assertEqual(asset_increase.prorata_date, start_of(self.today_1, 'month'))
        increase_method_number = 4 if self.today == self.end_month else 5
        self.assertEqual(asset_increase.method_number, increase_method_number)
        self.assertFalse(asset_increase.move_asset_on_run_id)

        if self.today == self.end_month:
            dep_moves_rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_1, 250),
                self._get_record_val_depreciation_move(self.end_month_2, 250),
                self._get_record_val_depreciation_move(self.end_month_3, 250),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 250),
            ]
            original_move_rec_vals = [
                self._get_record_val_depreciation_move(self.today, 1000),
            ]
            original_move_lines_rec_vals = [
                self._get_record_val_move_line(self.account_asset.id, debit=1000),
                self._get_record_val_move_line(self.account_asset_counterpart.id, credit=1000),
            ]
        else:
            dep_moves_rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_1, 200),
                self._get_record_val_depreciation_move(self.end_month_2, 200),
                self._get_record_val_depreciation_move(self.end_month_3, 200),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 200),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 200),
            ]
            original_move_rec_vals = [
                self._get_record_val_depreciation_move(self.today, 1000),
            ]
            original_move_lines_rec_vals = [
                self._get_record_val_move_line(self.account_asset.id, debit=1000),
                self._get_record_val_move_line(self.account_asset_counterpart.id, credit=1000),
            ]

        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', dep_moves_rec_vals)

        self.assertEqual(len(asset_increase.original_move_line_ids.mapped('move_id')), len(original_move_rec_vals))
        self.assertRecordValues(asset_increase.original_move_line_ids.mapped('move_id'), original_move_rec_vals)

        self._check_moves_lines(asset_increase.original_move_line_ids.mapped('move_id'), original_move_lines_rec_vals)

    def test_asset_modify_re_evaluate_increase_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_1,
            }
        )
        asset_modify.value_residual = 6000
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 1)

        asset_increase = self.bike.children_ids[0]

        self.assertEqual(asset_increase.product_id, self.bike.product_id)
        self.assertEqual(asset_increase.acquisition_date, self.today_1)
        self.assertEqual(asset_increase.prorata_date, start_of(self.today_2, 'month'))
        self.assertEqual(asset_increase.method_number, 4)
        self.assertFalse(asset_increase.move_asset_on_run_id)

        if self.today == self.end_month:
            dep_moves_rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_2, 500),
                self._get_record_val_depreciation_move(self.end_month_3, 500),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
            ]
            original_move_rec_vals = [
                self._get_record_val_depreciation_move(self.today_1, 2000),
            ]
            original_move_lines_rec_vals = [
                self._get_record_val_move_line(self.account_asset.id, debit=2000),
                self._get_record_val_move_line(self.account_asset_counterpart.id, credit=2000),
            ]
        else:
            dep_moves_rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_2, 250),
                self._get_record_val_depreciation_move(self.end_month_3, 250),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 250),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 250),
            ]
            original_move_rec_vals = [
                self._get_record_val_depreciation_move(self.today_1, 1000),
            ]
            original_move_lines_rec_vals = [
                self._get_record_val_move_line(self.account_asset.id, debit=1000),
                self._get_record_val_move_line(self.account_asset_counterpart.id, credit=1000),
            ]
        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', dep_moves_rec_vals)

        self.assertEqual(len(asset_increase.original_move_line_ids.mapped('move_id')), len(original_move_rec_vals))
        self.assertRecordValues(asset_increase.original_move_line_ids.mapped('move_id'), original_move_rec_vals)

        self._check_moves_lines(asset_increase.original_move_line_ids.mapped('move_id'), original_move_lines_rec_vals)

    def _asset_modify_pause_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'pause',
            }
        )
        asset_modify.pause()
        return asset_modify

    def test_asset_modify_pause_0(self):
        self._asset_modify_pause_0()

        moves = self.bike.depreciation_move_ids.filtered(lambda l: l.state == 'draft').sorted(
            key=lambda mv: (mv.date, mv.id)
        )
        self.assertEqual(len(moves), 0)

        self._check_0_posted_depreciation_moves()

    def test_asset_modify_pause_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'pause',
                'date': self.today_1,
            }
        )
        asset_modify.pause()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.today_1, 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_2(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'pause',
                'date': self.today_2,
            }
        )
        asset_modify.pause()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
            self._get_record_val_depreciation_move(self.today_2, 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_re_evaluate_increase_pause_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_residual = 6000
        asset_modify.modify()

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_residual = 7000
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 2)

        self._asset_modify_pause_0()

        increase_method_number = 4 if self.today == self.end_month else 5

        asset_increase = self.bike.children_ids[0]
        self.assertEqual(asset_increase.state, 'open')
        moves = asset_increase.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertEqual(len(moves), increase_method_number)

        asset_increase = self.bike.children_ids[1]
        self.assertEqual(asset_increase.state, 'open')
        moves = asset_increase.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertEqual(len(moves), increase_method_number)

    def test_asset_modify_re_evaluate_increase_pause_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_residual = 6000
        asset_modify.modify()

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_residual = 7000
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()
        self._check_initial_draft_depreciation_moves()

        self.assertEqual(len(self.bike.children_ids), 2)

        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'pause',
                'date': self.today_1,
            }
        )
        asset_modify.pause()

        increase_method_number = 4 if self.today == self.end_month else 5

        asset_increase = self.bike.children_ids[0]
        self.assertEqual(asset_increase.state, 'open')
        moves = asset_increase.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertEqual(len(moves), increase_method_number)

        asset_increase = self.bike.children_ids[1]
        self.assertEqual(asset_increase.state, 'open')
        moves = asset_increase.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertEqual(len(moves), increase_method_number)

    def test_asset_modify_pause_0_resume_0(self):
        self._asset_modify_pause_0()

        asset_modify = (
            self.env['asset.modify']
            .with_context(resume_after_pause=True)
            .create(
                {
                    'asset_id': self.bike.id,
                    'modify_action': 'resume',
                    'name': 'Re-evaluate Asset',
                }
            )
        )
        self.assertEqual(asset_modify.method_number, 10)
        self.assertEqual(asset_modify.value_residual, 4000)
        self.assertEqual(asset_modify.salvage_value, 0)

        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        if self.today == self.end_month:
            rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_1, 1000),
                self._get_record_val_depreciation_move(self.end_month_2, 1000),
                self._get_record_val_depreciation_move(self.end_month_3, 1000),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            ]
        else:
            rec_vals = [
                self._get_record_val_depreciation_move(self.end_month_1, 1000),
                self._get_record_val_depreciation_move(self.end_month_2, 1000),
                self._get_record_val_depreciation_move(self.end_month_3, 1000),
                self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_0_resume_1(self):
        self._asset_modify_pause_0()

        asset_modify = (
            self.env['asset.modify']
            .with_context(resume_after_pause=True)
            .create(
                {
                    'asset_id': self.bike.id,
                    'modify_action': 'resume',
                    'name': 'Re-evaluate Asset',
                    'date': self.today_1,
                }
            )
        )
        asset_modify.modify()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_end_month_0_resume_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'pause',
                'date': self.end_month,
            }
        )
        asset_modify.pause()

        asset_modify = (
            self.env['asset.modify']
            .with_context(resume_after_pause=True)
            .create(
                {
                    'asset_id': self.bike.id,
                    'modify_action': 'resume',
                    'name': 'Re-evaluate Asset',
                    'date': self.today_1,
                }
            )
        )
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_start_month_0_resume_start_month_1(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'pause',
            'date': start_of(self.today, 'month'),
        })
        asset_modify.pause()

        asset_modify = (
            self.env['asset.modify']
            .with_context(resume_after_pause=True)
            .create({
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'name': 'Re-evaluate Asset',
                'date': start_of(self.today_1, 'month'),
            })
        )
        asset_modify.modify()

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
            self._get_record_val_depreciation_move(start_of(self.today, 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_end_month_0_resume_start_month_1(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'pause',
            'date': self.end_month,
        })
        asset_modify.pause()

        asset_modify = (
            self.env['asset.modify']
            .with_context(resume_after_pause=True)
            .create({
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'name': 'Re-evaluate Asset',
                'date': start_of(self.today_1, 'month'),
            })
        )
        asset_modify.modify()

        self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 1000),
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_0_method_number_14_resume_0(self):
        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'method_number': 14,
                'name': 'Re-evaluate Asset',
            }
        )
        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 500),
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=3), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=4), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=5), 'month'), 500),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'method_number': 16,
                'name': 'Re-evaluate Asset',
            }
        )
        asset_modify.modify()

    def test_asset_modify_pause_0_method_number_14_resume_1(self):
        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'method_number': 14,
                'name': 'Re-evaluate Asset',
                'date': self.today_1,
            }
        )
        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=3), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=4), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=5), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=6), 'month'), 500),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_modify_pause_0_increase_value_resume_0(self):
        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'name': 'Re-evaluate Asset',
            }
        )
        asset_modify.value_re_evaluate = 2000
        asset_modify._onchange_value_re_evaluate()
        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

        self.assertEqual(len(self.bike.children_ids), 1)

        asset_increase = self.bike.children_ids[0]

        self.assertEqual(asset_increase.prorata_date, start_of(self.today_1, 'month'))
        increase_method_number = 4
        self.assertEqual(asset_increase.method_number, increase_method_number)
        self.assertFalse(asset_increase.move_asset_on_run_id)

        dep_moves_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 500),
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
        ]
        original_move_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month, 2000),
        ]
        original_move_lines_rec_vals = [
            self._get_record_val_move_line(self.account_asset.id, debit=2000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=2000),
        ]

        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', dep_moves_rec_vals)

        self.assertEqual(len(asset_increase.original_move_line_ids.mapped('move_id')), len(original_move_rec_vals))
        self.assertRecordValues(asset_increase.original_move_line_ids.mapped('move_id'), original_move_rec_vals)

        self._check_moves_lines(asset_increase.original_move_line_ids.mapped('move_id'), original_move_lines_rec_vals)

    def test_asset_modify_pause_0_increase_value_resume_1(self):
        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'value_residual': 6000,
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_1,
                'name': 'Re-evaluate Asset',
            }
        )

        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 1000),
            self._get_record_val_depreciation_move(self.end_month_3, 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 1000),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 1000),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

        self.assertEqual(len(self.bike.children_ids), 1)

        asset_increase = self.bike.children_ids[0]

        self.assertEqual(asset_increase.prorata_date, start_of(self.today_2, 'month'))
        increase_method_number = 4
        self.assertEqual(asset_increase.method_number, increase_method_number)
        self.assertFalse(asset_increase.move_asset_on_run_id)

        dep_moves_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
        ]
        original_move_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 2000),
        ]
        original_move_lines_rec_vals = [
            self._get_record_val_move_line(self.account_asset.id, debit=2000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=2000),
        ]

        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', dep_moves_rec_vals)

        self.assertEqual(len(asset_increase.original_move_line_ids.mapped('move_id')), len(original_move_rec_vals))
        self.assertRecordValues(asset_increase.original_move_line_ids.mapped('move_id'), original_move_rec_vals)

        self._check_moves_lines(asset_increase.original_move_line_ids.mapped('move_id'), original_move_lines_rec_vals)

    def test_asset_modify_pause_0_increase_value_method_number_14_resume_1(self):
        self._asset_modify_pause_0()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create(
            {
                'asset_id': self.bike.id,
                'modify_action': 'resume',
                'method_number': 14,
                'value_residual': 6000,
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'date': self.today_1,
                'name': 'Re-evaluate Asset',
            }
        )
        asset_modify.modify()

        self._check_0_posted_depreciation_moves()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=3), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=4), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=5), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=6), 'month'), 500),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

        self.assertEqual(len(self.bike.children_ids), 1)

        asset_increase = self.bike.children_ids[0]

        self.assertEqual(asset_increase.prorata_date, start_of(self.today_2, 'month'))
        increase_method_number = 8
        self.assertEqual(asset_increase.method_number, increase_method_number)
        self.assertFalse(asset_increase.move_asset_on_run_id)

        dep_moves_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_2, 250),
            self._get_record_val_depreciation_move(self.end_month_3, 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=3), 'month'), 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=4), 'month'), 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=5), 'month'), 250),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=6), 'month'), 250),
        ]
        original_move_rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 2000),
        ]
        original_move_lines_rec_vals = [
            self._get_record_val_move_line(self.account_asset.id, debit=2000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=2000),
        ]

        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', dep_moves_rec_vals)

        self.assertEqual(len(asset_increase.original_move_line_ids.mapped('move_id')), len(original_move_rec_vals))
        self.assertRecordValues(asset_increase.original_move_line_ids.mapped('move_id'), original_move_rec_vals)

        self._check_moves_lines(asset_increase.original_move_line_ids.mapped('move_id'), original_move_lines_rec_vals)

    def test_asset_modify_pause_end_prev_month_increase_value_method_number_14_resume_0(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'pause',
            'date': end_of(add(self.today, months=-1), 'month'),
        })
        asset_modify.pause()

        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create({
            'asset_id': self.bike.id,
            'modify_action': 'resume',
            'method_number': 15,
            'value_residual': 6000,
            'account_asset_counterpart_id': self.account_asset_counterpart.id,
            'date': self.today,
            'name': 'Re-evaluate Asset',
        })
        asset_modify.modify()

        if self.today == self.end_month:
            rec_vals = [
                self._get_record_val_depreciation_move(end_of(add(self.today, months=-5), 'month'), 1000),
                self._get_record_val_depreciation_move(end_of(add(self.today, months=-4), 'month'), 1000),
                self._get_record_val_depreciation_move(end_of(add(self.today, months=-3), 'month'), 1000),
                self._get_record_val_depreciation_move(end_of(add(self.today, months=-2), 'month'), 1000),
                self._get_record_val_depreciation_move(end_of(add(self.today, months=-1), 'month'), 1000),
            ]

            self._check_depreciation_moves(self.bike.depreciation_move_ids, 'posted', rec_vals)

            rec_vals = [
                self._get_record_val_move_line(self.account_depreciation.id, credit=1000),
                self._get_record_val_move_line(self.account_depreciation_expense.id, debit=1000),
            ]
            self._check_depreciation_move_last_line(self.bike.depreciation_move_ids, 'posted', rec_vals)
        else:
            self._check_initial_posted_depreciation_moves_n_last_lines()

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 500),
            self._get_record_val_depreciation_move(self.end_month_2, 500),
            self._get_record_val_depreciation_move(self.end_month_3, 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=1), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=2), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=3), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=4), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=5), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=6), 'month'), 500),
            self._get_record_val_depreciation_move(end_of(add(self.end_month_3, months=7), 'month'), 500),
        ]
        self._check_depreciation_moves(self.bike.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_method_50_50(self):
        self.assertEqual(self.asset_50_50.method, '50/50')
        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_method_50_50_dispose_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'dispose',
                'loss_account_id': self.account_dispose,
            }
        )
        asset_modify.sell_dispose()

        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 2)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
            self._get_record_val_depreciation_move(self.today, 10000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.asset_50_50.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.asset_50_50.account_depreciation_id.id, debit=5000),
            self._get_record_val_move_line(self.account_dispose.id, debit=5000),
        ]
        self._check_depreciation_move_last_line(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_method_50_50_dispose_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'dispose',
                'loss_account_id': self.account_dispose,
                'date': self.today_1,
            }
        )
        asset_modify.sell_dispose()

        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 2)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_depreciation_move(self.today_1, 10000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'draft', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.asset_50_50.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.asset_50_50.account_depreciation_id.id, debit=5000),
            self._get_record_val_move_line(self.account_dispose.id, debit=5000),
        ]
        self._check_depreciation_move_last_line(self.asset_50_50.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_method_50_50_sell_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'name': 'Held on sell asset 50/50',
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify_invoice = self.init_invoice(
            move_type='out_invoice',
            invoice_date=self.today,
            post=True,
            amounts=[1000],
        )
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 2)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
            self._get_record_val_depreciation_move(self.today, 10000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.asset_50_50.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.asset_50_50.account_depreciation_id.id, debit=5000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, debit=5000),
        ]
        self._check_depreciation_move_last_line(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.account_sell.id, debit=5000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=5000),
        ]
        self._check_moves_lines(self.asset_50_50.move_asset_sell_id, rec_vals)

    def test_asset_method_50_50_sell_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'sell',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
                'name': 'Held on sell asset 50/50',
                'date': self.today_1,
            }
        )
        asset_modify.action_held_for_sell()

        asset_modify_invoice = self.init_invoice(
            move_type='out_invoice',
            invoice_date=self.today_1,
            post=True,
            amounts=[1000],
        )
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'sell',
                'loss_account_id': self.account_sell,
                'invoice_ids': [asset_modify_invoice.id],
            }
        )
        asset_modify._onchange_invoice_ids()
        asset_modify.sell_dispose()

        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 2)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        rec_vals = [
            self._get_record_val_depreciation_move(self.today_1, 10000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'draft', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.asset_50_50.account_asset_id.id, credit=10000),
            self._get_record_val_move_line(self.asset_50_50.account_depreciation_id.id, debit=5000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, debit=5000),
        ]
        self._check_depreciation_move_last_line(self.asset_50_50.depreciation_move_ids, 'draft', rec_vals)

        rec_vals = [
            self._get_record_val_move_line(self.account_sell.id, debit=5000),
            self._get_record_val_move_line(self.account_asset_counterpart.id, credit=5000),
        ]
        self._check_moves_lines(self.asset_50_50.move_asset_sell_id, rec_vals)

    def test_asset_method_50_50_re_evaluate_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'date': self.today,
            }
        )
        asset_modify.modify()

        self.assertEqual(len(self.asset_50_50.children_ids), 0)
        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_method_50_50_re_evaluate_1(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'date': self.today_1,
            }
        )
        asset_modify.modify()

        self.assertEqual(len(self.asset_50_50.children_ids), 0)
        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_method_50_50_re_evaluate_increase_0(self):
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': self.asset_50_50.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
            }
        )
        asset_modify.value_re_evaluate = 1000
        asset_modify._onchange_value_re_evaluate()
        asset_modify.modify()

        self.assertEqual(len(self.asset_50_50.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 5000),
        ]
        self._check_depreciation_moves(self.asset_50_50.depreciation_move_ids, 'posted', rec_vals)

        self.assertEqual(len(self.asset_50_50.children_ids), 1)

        asset_increase = self.asset_50_50.children_ids[0]
        self.assertEqual(asset_increase.method_number, self.asset_50_50.method_number)
        self.assertEqual(len(asset_increase.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 500),
        ]
        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', rec_vals)

    def test_asset_child_re_evaluate_line(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'modify',
            'value_residual': 16000,
            'name': 'Re-evaluate Asset',
            'account_asset_counterpart_id': self.account_asset_counterpart.id,
        })
        asset_modify.modify()

        self.assertEqual(len(self.bike.children_ids), 1)

        move_line_ids = self.bill_in_invoice.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_capital_investment
        )
        asset_child = self.bike.children_ids[0]

        asset_child.write({
            're_evaluate_line_ids': [Command.create({'asset_id': asset_child.id, 're_evaluate_move_line_id': move_line_ids[0].id})],
        })

        rec_vals = [{
            'asset_id': asset_child.id,
            're_evaluate_move_line_id': move_line_ids[0].id,
            'value_re_evaluate_move_line': move_line_ids[0].balance,
            'value_re_evaluate': move_line_ids[0].balance,
        }]
        self.assertEqual(len(asset_child.re_evaluate_line_ids), len(rec_vals))
        self.assertRecordValues(asset_child.re_evaluate_line_ids, rec_vals)

    def test_asset_child_re_evaluate_line_increase_value_re_evaluate(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'modify',
            'value_residual': 16000,
            'name': 'Re-evaluate Asset',
            'account_asset_counterpart_id': self.account_asset_counterpart.id,
        })
        asset_modify.modify()

        self.assertEqual(len(self.bike.children_ids), 1)

        move_line_ids = self.bill_in_invoice.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_capital_investment
        )
        asset_child = self.bike.children_ids[0]

        try:
            asset_child.write({
                're_evaluate_line_ids': [Command.create({
                    'asset_id': asset_child.id,
                    're_evaluate_move_line_id': move_line_ids[0].id,
                    'value_re_evaluate': move_line_ids[0].balance + 1000,
                })],
            })
            self.fail("Value Re-evaluate must be less than Value Re-evaluate Move Line")
        except UserError:
            pass

    def test_asset_child_re_evaluate_line_increase_value_re_evaluate_book_value(self):
        asset_modify = self.env['asset.modify'].create({
            'asset_id': self.bike.id,
            'modify_action': 'modify',
            'value_residual': 6000,
            'name': 'Re-evaluate Asset',
            'account_asset_counterpart_id': self.account_asset_counterpart.id,
        })
        asset_modify.modify()

        self.assertEqual(len(self.bike.children_ids), 1)

        move_line_ids = self.bill_in_invoice.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_capital_investment
        )
        asset_child = self.bike.children_ids[0]

        try:
            asset_child.write({
                're_evaluate_line_ids': [Command.create({
                    'asset_id': asset_child.id,
                    're_evaluate_move_line_id': move_line_ids[0].id,
                    'value_re_evaluate': move_line_ids[0].balance,
                })],
            })
            self.fail("Value Re-evaluate shouldn`t be more than Book Value")
        except UserError:
            pass

    def test_asset_method_100(self):
        self.assertEqual(self.asset_100.method, '100')
        self.assertEqual(self.asset_100.method_period, '1')
        self.assertEqual(self.asset_100.method_number, 1)

        self.assertEqual(len(self.asset_100.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 10000),
        ]
        self._check_depreciation_moves(self.asset_100.depreciation_move_ids, 'posted', rec_vals)

    def test_asset_method_100_re_evaluate_increase_0(self):
        asset_modify = self.env['asset.modify'].create({
                'asset_id': self.asset_100.id,
                'modify_action': 'modify',
                'name': 'Re-evaluate Asset',
                'account_asset_counterpart_id': self.account_asset_counterpart.id,
        })
        asset_modify.value_re_evaluate = 1000
        asset_modify._onchange_value_re_evaluate()
        asset_modify.modify()

        self.assertEqual(len(self.asset_100.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(self.start_date, months=1), 'month'), 10000),
        ]
        self._check_depreciation_moves(self.asset_100.depreciation_move_ids, 'posted', rec_vals)

        self.assertEqual(len(self.asset_100.children_ids), 1)

        asset_increase = self.asset_100.children_ids[0]
        self.assertEqual(asset_increase.method_number, self.asset_100.method_number)
        self.assertEqual(len(asset_increase.depreciation_move_ids), 1)

        rec_vals = [
            self._get_record_val_depreciation_move(self.end_month_1, 1000),
        ]
        self._check_depreciation_moves(asset_increase.depreciation_move_ids, 'draft', rec_vals)

    def test_commissioning_date(self):
        try:
            asset = self.env['account.asset'].create(
                {
                    'product_id': self.product_bike.id,
                    'account_capital_investment_id': self.account_capital_investment.id,
                    'account_asset_id': self.account_asset.id,
                    'account_depreciation_id': self.account_depreciation.id,
                    'account_depreciation_expense_id': self.account_depreciation_expense.id,
                    'journal_id': self.company_data['default_journal_misc'].id,
                    'asset_type': 'purchase',
                    'name': 'bike',
                    'acquisition_date': self.start_date,
                    'commissioning_date': add(self.start_date, months=-1),
                    'original_value': 10000,
                    'method_number': 10,
                    'method_period': '1',
                    'method': 'linear',
                }
            )
            self.fail("The date of commissioning cannot be earlier than the date of purchase")
        except UserError:
            pass

    def test_create_equipment(self):
        self.assertFalse(self.bike.equipment_id)
        self.bike.action_create_equipment()
        self.assertTrue(self.bike.equipment_id)

        self.assertEqual(self.bike.equipment_id.name, self.bike.name)
        self.assertEqual(self.bike.equipment_id.cost, self.bike.original_value)

        with self.assertRaises(UserError):
            self.bike.action_create_equipment()

    def test_asset_double_pause(self):
        acquisition_date = fields.Date.to_date('2023-06-08')
        cur_bike = self.env['account.asset'].create(
            {
                'product_id': self.product_bike.id,
                'account_capital_investment_id': self.account_capital_investment.id,
                'account_asset_id': self.account_asset.id,
                'account_depreciation_id': self.account_depreciation.id,
                'account_depreciation_expense_id': self.account_depreciation_expense.id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'bike',
                'acquisition_date': acquisition_date,
                'commissioning_date': acquisition_date,
                'original_value': 45000,
                'method_number': 36,
                'method_period': '1',
                'method': 'linear',
            }
        )
        cur_bike.validate()

        pause_date_0 = fields.Date.to_date('2023-09-06')
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': cur_bike.id,
                'modify_action': 'pause',
                'date': pause_date_0,
            }
        )
        asset_modify.pause()
        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=1), 'month'), 1250),
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=2), 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_0, 1250),
        ]
        self._check_depreciation_moves(cur_bike.depreciation_move_ids, 'posted', rec_vals)
        self.assertFalse(cur_bike.depreciation_move_ids.filtered(lambda r: r.state == 'draft'))

        resume_date_0 = fields.Date.to_date('2023-10-04')
        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create({
            'asset_id': cur_bike.id,
            'modify_action': 'resume',
            'date': resume_date_0,
            'name': 'Re-evaluate Asset',
        })
        asset_modify.modify()

        pause_date_1 = fields.Date.to_date('2023-12-13')
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': cur_bike.id,
                'modify_action': 'pause',
                'date': pause_date_1,
            }
        )
        asset_modify.pause()
        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=1), 'month'), 1250),
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=2), 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_0, 1250),
            self._get_record_val_depreciation_move(end_of(add(resume_date_0, months=1), 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_1, 1250),
        ]
        self._check_depreciation_moves(cur_bike.depreciation_move_ids, 'posted', rec_vals)
        self.assertFalse(cur_bike.depreciation_move_ids.filtered(lambda r: r.state == 'draft'))

        resume_date_1 = fields.Date.to_date('2024-01-10')
        asset_modify = self.env['asset.modify'].with_context(resume_after_pause=True).create({
            'asset_id': cur_bike.id,
            'modify_action': 'resume',
            'date': resume_date_1,
            'name': 'Re-evaluate Asset',
        })
        asset_modify.modify()

        pause_date_2 = fields.Date.to_date('2024-02-13')
        asset_modify = self.env['asset.modify'].create(
            {
                'asset_id': cur_bike.id,
                'modify_action': 'pause',
                'date': pause_date_2,
            }
        )
        asset_modify.pause()
        rec_vals = [
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=1), 'month'), 1250),
            self._get_record_val_depreciation_move(end_of(add(acquisition_date, months=2), 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_0, 1250),
            self._get_record_val_depreciation_move(end_of(add(resume_date_0, months=1), 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_1, 1250),
            self._get_record_val_depreciation_move(end_of(resume_date_1, 'month'), 1250),
            self._get_record_val_depreciation_move(pause_date_2, 1250),
        ]
        self._check_depreciation_moves(cur_bike.depreciation_move_ids, 'posted', rec_vals)
        self.assertFalse(cur_bike.depreciation_move_ids.filtered(lambda r: r.state == 'draft'))
