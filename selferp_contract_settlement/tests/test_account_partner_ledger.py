import logging

from itertools import combinations

from odoo import models, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from .common import AccountContractTestCommon


_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestPartnerLedgerCustomHandler(TestAccountReportsCommon, AccountContractTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.AccountContract = cls.env['account.contract']
        cls.AccountMoveLine = cls.env['account.move.line']

        # switch lang to en_US for check 'Undefined' string value
        cls.report = cls.env.ref('account_reports.partner_ledger_report').with_context(lang='en_US')

        #
        # fill test data
        #
        cls.partner_line_id = cls.report._get_generic_line_id(cls.partner_a._name, cls.partner_a.id)
        cls.contract_1 = cls.contract_pa_1_p
        cls.contract_2 = cls.contract_pa_2_s
        cls.date_test_start = fields.Date.from_string('2023-01-01')
        cls.date_test = fields.Date.from_string('2023-01-15')
        cls.date_test_end = fields.Date.from_string('2023-01-31')
        cls.date_test_start2 = fields.Date.from_string('2023-02-01')
        cls.date_test2 = fields.Date.from_string('2023-02-15')
        cls.date_test_end2 = fields.Date.from_string('2023-12-31')

        # create move lines
        cls.test_move_lines = (
            cls.register_move(cls.contract_2, -150.00, invoice_date=cls.date_test, override_move_date=True) +
            cls.register_move(cls.contract_1, -100.00, invoice_date=cls.date_test, override_move_date=True) +
            cls.register_move(cls.contract_2, 300.00, invoice_date=cls.date_test, override_move_date=True) +
            cls.register_move(None, 200.00, invoice_date=cls.date_test, override_move_date=True) +
            cls.register_move(None, -120.00, invoice_date=cls.date_test, override_move_date=True)
        )

        cls.contracts_info = [
            (cls.contract_1,    cls.contract_1.id,  cls.contract_1.display_name,    0.0,            100.0 * 1.2),
            (cls.contract_2,    cls.contract_2.id,  cls.contract_2.display_name,    300.0 * 1.2,    150.0 * 1.2),
            (None,              None,               "Undefined",                    200.0 * 1.2,    120.0 * 1.2),
        ]
        cls.initial_balance = (
            sum(map(lambda r: r[3], cls.contracts_info)),
            sum(map(lambda r: r[4], cls.contracts_info)),
            sum(map(lambda r: r[3] - r[4], cls.contracts_info)),
        )

    @classmethod
    def _generate_options_groupby_contract(cls, date_from, date_to, default_options=None):
        return cls._generate_options(
            cls.report,
            fields.Date.from_string(date_from),
            fields.Date.from_string(date_to),
            default_options=default_options,
        )

    @classmethod
    def _get_lines(cls, options, without_initials=True, without_totals=True):
        # call report
        lines = cls.report._get_lines(options)

        # filter result
        result_lines = []
        for line in lines:
            if line.get('parent_id') and line.get('parent_id').startswith(cls.partner_line_id):
                markup, record_model, record_id = cls.report._parse_line_id(line.get('id'))[-1]
                if (not without_initials or markup != 'initial') and (not without_totals or markup != 'total'):
                    result_lines.append(line)

        return result_lines

    def test_groupby_contract_ungrouped(self):
        """ Test ungrouped lines for expanded partner

        :return:
        """
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start,
            date_to=self.date_test_end,
            default_options={
                'groupby_contract': False,
                'unfolded_lines': [
                    self.partner_line_id,
                ],
            },
        )

        self._check_groupby_contract_ungrouped(options)

    def test_groupby_contract_ungrouped_unfold_all(self):
        """ Test ungrouped lines for expanded partner

        :return:
        """
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start,
            date_to=self.date_test_end,
            default_options={
                'groupby_contract': False,
                'unfolded_lines': [
                    self.partner_line_id,
                ],
                'unfold_all': True,
            },
        )

        self._check_groupby_contract_ungrouped(options)

    def _check_groupby_contract_ungrouped(self, options):
        lines = self._get_lines(options)

        self.assertEqual(len(lines), len(self.test_move_lines))

        self._check_positions(
            lines,
            [(r._name, r.id) for r in self.test_move_lines],
        )

        self._check_move_lines(lines, self.test_move_lines, False)

    def test_groupby_contract_grouped_unfold_all(self):
        """ Test grouped lines for expanded partner and
            expanded Contract(s) in different combinations

        :return:
        """
        self._check_groupby_contract_grouped(
            unfolded_contracts=[
                self.contract_1.id,
                self.contract_2.id,
                None,
            ],
            extra_options={
                'unfold_all': True,
            }
        )

    def test_groupby_contract_grouped(self):
        """ Test grouped lines for expanded partner and
            expanded Contract(s) in different combinations

        :return:
        """
        contract_ids = [
            self.contract_1.id,
            self.contract_2.id,
            None,
        ]

        # prepare all combinations
        contract_ids_combinations = sum([list(map(list, combinations(contract_ids, i))) for i in range(len(contract_ids) + 1)], [])

        # run tests for this combination
        for contract_ids_combination in contract_ids_combinations:
            _logger.info("UNFOLD contracts: %s" % contract_ids_combination)
            self._check_groupby_contract_grouped(unfolded_contracts=contract_ids_combination)

    def test_initial_balance_only_ungrouped(self):
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start2,
            date_to=self.date_test_end2,
            default_options={
                'groupby_contract': False,
                'unfolded_lines': [
                    self.partner_line_id,
                ],
            },
        )

        lines = self._get_lines(options, without_initials=False)

        self.assertEqual(len(lines), 1)

        self._check_positions(
            lines,
            [('initial', self.initial_balance)],
        )

    def test_initial_balance_only_grouped(self):
        """ Test grouped lines for expanded partner and
            expanded Contract(s) in different combinations
            (initial balances lines only)

        :return:
        """
        contract_ids = [
            self.contract_1.id,
            self.contract_2.id,
            None,
        ]

        # prepare all combinations
        contract_ids_combinations = sum([list(map(list, combinations(contract_ids, i))) for i in range(len(contract_ids) + 1)], [])

        # run tests for this combination
        for contract_ids_combination in contract_ids_combinations:
            _logger.info("UNFOLD contracts (initial balance): %s" % contract_ids_combination)
            self._check_groupby_contract_grouped_initial_balances(unfolded_contracts=contract_ids_combination)

    def test_initial_balance_plus_grouped(self):
        # register new move line
        new_move_line = self.register_move(self.contract_2, 1000, invoice_date=self.date_test2)

        # get report options
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start2,
            date_to=self.date_test_end2,
            default_options={
                'groupby_contract': True,
                'unfolded_lines': [
                    self.partner_line_id,
                    self.report._get_generic_line_id(
                        self.AccountContract._name,
                        self.contract_2.id,
                        parent_line_id=self.partner_line_id,
                    )
                ],
            },
        )

        lines = self._get_lines(options, without_initials=False)

        self.assertEqual(len(lines), 1 + len(self.contracts_info) + 1 + 1)

        self._check_positions(
            lines,
            [
                ('initial', self.initial_balance),
                (self.AccountContract._name, self.contract_1.id),
                (self.AccountContract._name, self.contract_2.id),
                ('initial', (self.contracts_info[1][3], self.contracts_info[1][4], self.contracts_info[1][3] - self.contracts_info[1][4])),
                (self.AccountMoveLine._name, new_move_line.id),
                (self.AccountContract._name, None),
            ],
        )

        contract_lines = list(filter(lambda r: r.get('is_contract'), lines))
        self.assertEqual(len(contract_lines), 3)
        self._check_contracts(
            contract_lines,
            self.contracts_info,
            {
                self.contract_2.id: {
                    'debit': new_move_line.amount_currency,
                },
            },
        )

        account_move_lines = list(filter(lambda r: r.get('caret_options') == self.AccountMoveLine._name, lines))
        self.assertEqual(len(account_move_lines), 1)
        self._check_move_lines(account_move_lines, new_move_line, True)

    def _check_groupby_contract_grouped(self, unfolded_contracts=[], extra_options={}):
        unfolded_lines = []
        move_lines = self.AccountMoveLine.browse()
        move_lines_map = {}

        contract_ids = list(map(lambda r: isinstance(r, models.Model) and r.id or r, unfolded_contracts or []))

        for contract_id in contract_ids:
            unfolded_lines.append(self.report._get_generic_line_id(
                self.AccountContract._name,
                contract_id,
                parent_line_id=self.partner_line_id,
            ))

            amls = self.test_move_lines.filtered(
                lambda r: (contract_id and r.contract_id and r.contract_id.id == contract_id)
                          or (not contract_id and not r.contract_id)
            )
            move_lines_map[contract_id] = amls
            move_lines += amls

        options = {
            'groupby_contract': True,
            'unfolded_lines': [
                self.partner_line_id,
            ] + unfolded_lines,
        }
        if extra_options:
            options.update(extra_options)
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start,
            date_to=self.date_test_end,
            default_options=options,
        )

        lines = self._get_lines(options)

        self.assertEqual(len(lines), 3 + len(move_lines))

        self._check_positions(
            lines,
            [
                (self.AccountContract._name, self.contract_1.id),
            ] + [
                (r._name, r.id) for r in move_lines_map.get(self.contract_1.id) or []
            ] + [
                (self.AccountContract._name, self.contract_2.id),
            ] + [
                (r._name, r.id) for r in move_lines_map.get(self.contract_2.id) or []
            ] + [
                (self.AccountContract._name, None),
            ] + [
                (r._name, r.id) for r in move_lines_map.get(None) or []
            ],
        )

        contract_lines = list(filter(lambda r: r.get('is_contract'), lines))
        self.assertEqual(len(contract_lines), 3)
        self._check_contracts(contract_lines, self.contracts_info)

        account_move_lines = list(filter(lambda r: r.get('caret_options') == self.AccountMoveLine._name, lines))
        self.assertEqual(len(account_move_lines), len(move_lines))
        self._check_move_lines(account_move_lines, move_lines, True)

    def _check_groupby_contract_grouped_initial_balances(self, unfolded_contracts=[], extra_options={}):
        contract_ids = list(map(lambda r: isinstance(r, models.Model) and r.id or r, unfolded_contracts or []))
        unfolded_lines = []

        for contract_id in contract_ids:
            unfolded_lines.append(self.report._get_generic_line_id(
                self.AccountContract._name,
                contract_id,
                parent_line_id=self.partner_line_id,
            ))

        options = {
            'groupby_contract': True,
            'unfolded_lines': [
                self.partner_line_id,
            ] + unfolded_lines,
        }
        if extra_options:
            options.update(extra_options)
        options = self._generate_options_groupby_contract(
            date_from=self.date_test_start2,
            date_to=self.date_test_end2,
            default_options=options,
        )

        lines = self._get_lines(options, without_initials=False)

        self.assertEqual(len(lines), 1 + len(self.contracts_info) + len(unfolded_lines))

        expected_lines = [('initial', self.initial_balance)]
        for i, contract_info in enumerate(self.contracts_info):
            expected_lines.append((self.AccountContract._name, contract_info[1]))
            if contract_info[1] in contract_ids:
                expected_lines.append(('initial', (contract_info[3], contract_info[4], contract_info[3] - contract_info[4])))

        self._check_positions(lines, expected_lines)

        contract_lines = list(filter(lambda r: r.get('is_contract'), lines))
        self.assertEqual(len(contract_lines), 3)
        self._check_contracts(contract_lines, self.contracts_info)

    def _check_move_lines(self, lines, move_lines, group_by_contract):
        for i, line in enumerate(lines):
            move_line = move_lines[i]

            parent_line_id = self.partner_line_id
            if group_by_contract:
                parent_line_id = self.report._get_generic_line_id(
                    self.AccountContract._name,
                    move_line.contract_id and move_line.contract_id.id or None,
                    parent_line_id=parent_line_id
                )

            self.assertEqual(line['id'], self.report._get_generic_line_id(move_line._name, move_line.id, parent_line_id=parent_line_id))
            self.assertEqual(line['level'], 4)
            self.assertEqual(line['caret_options'], self.AccountMoveLine._name)
            self.assertIsNone(line.get('is_contract'))
            self.assertEqual(line['columns'][5]['no_format'], move_line.debit)
            self.assertEqual(line['columns'][6]['no_format'], move_line.credit)
            self.assertEqual(line['columns'][7]['no_format'], move_line.amount_currency)

    def _check_contracts(self, lines, contracts, contracts_extra=None):
        for i, contract_info in enumerate(contracts):
            line = lines[i]
            line_id = self.report._get_generic_line_id(
                self.AccountContract._name,
                contract_info[1],
                parent_line_id=self.partner_line_id,
            )

            contract_info_extra = (contracts_extra or {}).get(contract_info[1]) or {}
            extra_debit = contract_info_extra.get('debit') or 0.00
            extra_credit = contract_info_extra.get('credit') or 0.00

            self.assertEqual(line['id'], line_id)
            self.assertEqual(line['level'], 3)
            self.assertIsNone(line.get('caret_options'))
            self.assertTrue(line.get('is_contract'))
            self.assertEqual(line['name'], contract_info[2])
            self.assertEqual(line['columns'][5]['no_format'], contract_info[3] + extra_debit)
            self.assertEqual(line['columns'][6]['no_format'], contract_info[4] + extra_credit)
            self.assertEqual(line['columns'][8]['no_format'], contract_info[3] - contract_info[4] + extra_debit - extra_credit)

    def _check_positions(self, lines, sequence):
        self.assertEqual(len(lines), len(sequence))

        for i, seq in enumerate(sequence):
            line = lines[i]
            markup, model, record_id = self.report._parse_line_id(line.get('id'))[-1]

            if markup == 'initial':
                self.assertEqual(markup, seq[0])
                self.assertTrue(not model)
                self.assertTrue(not record_id)

                self.assertEqual(line['columns'][5]['no_format'], seq[1][0])
                self.assertEqual(line['columns'][6]['no_format'], seq[1][1])
                self.assertEqual(line['columns'][8]['no_format'], seq[1][2])

            else:
                if seq[0] == self.AccountContract._name:
                    self.assertTrue(line.get('is_contract'))
                else:
                    self.assertEqual(line.get('caret_options'), seq[0])

                self.assertTrue(not markup)
                self.assertEqual(model, seq[0])
                self.assertEqual(record_id, seq[1])
