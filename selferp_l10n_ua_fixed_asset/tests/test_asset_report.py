from odoo import fields
from odoo.tests import tagged
from odoo.tools import add, start_of, end_of, format_date

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAssetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.AccountAsset = cls.env['account.asset']
        cls.AccountAccount = cls.env['account.account']

        cls.today = fields.Date.today()

        cls.report = cls.env.ref('account_asset.assets_report')
        cls.options = cls._generate_options(
            cls.report,
            start_of(cls.today, 'month'),
            end_of(cls.today, 'month'),
        )

        company_id = cls.company_data['company'].id
        cls.account_capital_investment = cls.AccountAccount.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '151000'),
            ],
            limit=1,
        )
        cls.account_asset = cls.AccountAccount.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '100000'),
            ],
            limit=1,
        )
        cls.account_depreciation = cls.AccountAccount.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '131000'),
            ],
            limit=1,
        )
        cls.account_depreciation.write({'account_type': 'asset_fixed'})
        cls.account_depreciation_expense = cls.AccountAccount.search(
            [
                ('company_id', '=', company_id),
                ('code', '=', '920000'),
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

        cls.start_date = start_of(add(cls.today, months=-6), 'month')
        cls.asset_1 = cls.AccountAsset.create(
            {
                'product_id': cls.product_bike.id,
                'account_capital_investment_id': cls.account_capital_investment.id,
                'account_asset_id': cls.account_asset.id,
                'account_depreciation_id': cls.account_depreciation.id,
                'account_depreciation_expense_id': cls.account_depreciation_expense.id,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'asset_1',
                'asset_number': 'number_asset_1',
                'acquisition_date': cls.start_date,
                'commissioning_date': cls.start_date,
                'original_value': 10000,
                'method_number': 10,
                'method_period': '1',
                'method': 'linear',
            }
        )
        cls.asset_1.validate()

        cls.asset_2 = cls.AccountAsset.create(
            {
                'account_capital_investment_id': cls.account_capital_investment.id,
                'account_asset_id': cls.account_asset.id,
                'account_depreciation_id': cls.account_depreciation.id,
                'account_depreciation_expense_id': cls.account_depreciation_expense.id,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'asset_1',
                'asset_number': 'number_asset_2',
                'acquisition_date': cls.start_date,
                'commissioning_date': cls.start_date,
                'original_value': 15000,
                'method_number': 15,
                'method_period': '1',
                'method': '100',
            }
        )
        cls.asset_2.validate()

        cls.asset_3 = cls.AccountAsset.create(
            {
                'account_capital_investment_id': cls.account_capital_investment.id,
                'account_asset_id': cls.account_asset.id,
                'account_depreciation_id': cls.account_depreciation.id,
                'account_depreciation_expense_id': cls.account_depreciation_expense.id,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'asset_type': 'purchase',
                'name': 'asset_1',
                'asset_number': 'number_asset_2',
                'acquisition_date': cls.start_date,
                'commissioning_date': cls.start_date,
                'original_value': 15000,
                'method_number': 15,
                'method_period': '1',
                'method': '50/50',
            }
        )
        cls.asset_3.validate()

    def test_presence_columns(self):
        self.assertEqual(self.options['columns'][0]['expression_label'], 'acquisition_date_ua')
        self.assertEqual(self.options['columns'][1]['expression_label'], 'commissioning_date')
        self.assertEqual(self.options['columns'][2]['expression_label'], 'asset_number')
        self.assertEqual(self.options['columns'][3]['expression_label'], 'asset_original_value')

    @staticmethod
    def _line_seq(level, model='', record_id=None, columns=None):
        return {
            'level': level,
            'model': model,
            'record_id': record_id,
            'columns': columns or {},
        }

    def test_add_columns_assets_2(self):
        lines = self.report._get_lines(self.options)

        cols_asset_1 = {
            'acquisition_date_ua': format_date(self.env, self.asset_1.acquisition_date),
            'commissioning_date': format_date(self.env, self.asset_1.commissioning_date),
            'asset_number': self.asset_1.asset_number,
            'asset_original_value': self.asset_1.original_value,
            'method': 'Linear',
            'duration_rate': '10 m',
        }
        cols_asset_2 = {
            'acquisition_date_ua': format_date(self.env, self.asset_2.acquisition_date),
            'commissioning_date': format_date(self.env, self.asset_2.commissioning_date),
            'asset_number': self.asset_2.asset_number,
            'asset_original_value': self.asset_2.original_value,
            'method': '100%',
            'duration_rate': '1 y 3 m',
        }
        cols_asset_3 = {
            'acquisition_date_ua': format_date(self.env, self.asset_2.acquisition_date),
            'commissioning_date': format_date(self.env, self.asset_2.commissioning_date),
            'asset_number': self.asset_2.asset_number,
            'asset_original_value': self.asset_2.original_value,
            'method': '50/50',
            'duration_rate': '1 y 3 m',
        }
        sequence = [
            self._line_seq(1, self.AccountAccount._name, self.account_asset.id),
            self._line_seq(2, self.AccountAsset._name, self.asset_1.id, cols_asset_1),
            self._line_seq(2, self.AccountAsset._name, self.asset_2.id, cols_asset_2),
            self._line_seq(2, self.AccountAsset._name, self.asset_3.id, cols_asset_3),
            self._line_seq(2),
            self._line_seq(1),
        ]

        self.assertEqual(len(lines), len(sequence))

        partner_line_id = self.report._get_generic_line_id(self.AccountAccount._name, self.account_asset.id)

        for i, seq in enumerate(sequence):
            line = lines[i]
            markup, model, record_id = self.report._parse_line_id(line['id'])[-1]

            line_id = self.report._get_generic_line_id(
                seq['model'],
                seq['record_id'],
                markup=markup,
                parent_line_id=partner_line_id if seq['level'] == 2 else None,
            )

            self.assertEqual(line['id'], line_id)
            self.assertEqual(line['level'], seq['level'])
            self.assertEqual(line['columns'][0].get('no_format'), seq['columns'].get('acquisition_date_ua'))
            self.assertEqual(line['columns'][1].get('no_format'), seq['columns'].get('commissioning_date'))
            self.assertEqual(line['columns'][2].get('no_format'), seq['columns'].get('asset_number'))
            self.assertEqual(line['columns'][3].get('no_format'), seq['columns'].get('asset_original_value'))
            self.assertEqual(line['columns'][5].get('no_format'), seq['columns'].get('method'))
            self.assertEqual(line['columns'][6].get('no_format'), seq['columns'].get('duration_rate'))
