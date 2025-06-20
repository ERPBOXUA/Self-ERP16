import datetime

from collections import namedtuple

from odoo import fields, Command
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from .common import VATTestCommonPriceVATIncl


LineInfo = namedtuple(
    'LineInfo',
    ['id', 'parent_id', 'level', 'name', 'journal', 'account', 'debit', 'credit', 'balance', 'first_event', 'vat'],
)


@tagged('post_install', '-at_install')
class TestAccountReportVATFirstEvent(TestAccountReportsCommon, VATTestCommonPriceVATIncl):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # switch lang to en_US for check 'Undefined' string value
        cls.report = cls.env.ref('selferp_l10n_ua_vat.account_report_vat_first_event').with_context(lang='en_US')

        cls.AccountMoveLine = cls.env['account.move.line']
        cls.AccountContract = cls.env['account.contract']
        cls.SaleOrder = cls.env['sale.order']

        property_account_receivable = cls.company_data['default_account_receivable']
        property_account_receivable.first_event = True

        cls.partner_a.tracking_first_event = 'in_general'

        cls.partner_b.write({
            'tracking_first_event': 'by_contract',
            'property_account_receivable_id': property_account_receivable.id,
            # This is forcing the payment term 'Immediate payment' (inherited one is using '30% advance' payment term
            # which causes creating additional move lines)
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
        })

        cls.partner_c = cls.env['res.partner'].create({
            'name': 'partner_c',
            'tracking_first_event': 'by_order',
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })

        cls.date_test_start = fields.Date.from_string('2023-03-01')
        cls.date_test_end = fields.Date.from_string('2023-03-31')

    @classmethod
    def get_move_line_menu_tag(cls, move_line):
        if move_line.vat_invoice_id and move_line.vat_first_event_move_id:
            car_opt = ':with_vat_invoice_and_first_event'
        elif not move_line.vat_invoice_id and move_line.vat_first_event_move_id:
            car_opt = ':with_first_event'
        elif move_line.vat_invoice_id and not move_line.vat_first_event_move_id:
            car_opt = ':with_vat_invoice'
        else:
            car_opt = ''
        return car_opt

    @classmethod
    def register_move_lines(cls, move):
        return move.line_ids.filtered(lambda l: l.account_id.first_event and l.account_id.account_type == 'asset_receivable')

    def test_general_case1(self):
        partner_line_id = self.report._get_generic_line_id(self.partner_a._name, self.partner_a.id)

        test_move_lines = (
            self.register_move_from_payment(self.partner_a, 10000, datetime.datetime(2023, 3, 1)) +
            self.register_move_from_payment(self.partner_a, 15000, datetime.datetime(2023, 3, 2)) +
            self.register_move_from_invoice(self.partner_a, datetime.datetime(2023, 3, 3), [(self.product_a, 30000)]) +
            self.register_move_from_invoice(self.partner_a, datetime.datetime(2023, 3, 4), [(self.product_a, 45000)]) +
            self.register_move_from_payment(self.partner_a, 40000, datetime.datetime(2023, 3, 6)) +
            self.register_move_from_payment(self.partner_a, 30000, datetime.datetime(2023, 3, 6))
        )

        first_event = [
            10000.0,
            15000.0,
            5000.0,
            45000.0,
            # Payment of 40000 generates 2 lines !!!
            0.0,
            0.0,
            20000.0,
        ]

        options = TestAccountReportVATFirstEvent._generate_options(
            self.report,
            self.date_test_start,
            self.date_test_end,
            default_options={
                'unfold_all': True,
                'unfolded_lines': [],
                'tracking_first_event': 'in_general',
            },
        )

        lines = self.get_lines(options, partner_line_id=partner_line_id)

        self.assertTrue(lines)

        for i, line in enumerate(lines):
            move_line = test_move_lines[i]

            self.assertEqual(line['id'], self.report._get_generic_line_id(move_line._name, move_line.id, parent_line_id=partner_line_id))
            self.assertEqual(line['level'], 2)
            self.assertEqual(line['caret_options'], self.AccountMoveLine._name)

            self.assertEqual(line['columns'][2]['no_format'], move_line.debit)
            self.assertEqual(line['columns'][3]['no_format'], move_line.credit)
            self.assertEqual(line['columns'][5]['no_format'], first_event[i])

        # Check folded report lines

        self.check_moves_positions(
            {
                'unfold_all': False,
                'tracking_first_event': 'in_general',
                'unfolded_lines': [],
            },
            test_move_lines,
            partner_line_id=partner_line_id,
        )

    def test_contract_case1(self):
        # Prepare data
        event_date_01 = datetime.datetime(2023, 3, 1)
        event_date_02 = datetime.datetime(2023, 3, 2)
        event_date_03 = datetime.datetime(2023, 3, 3)

        product_1 = self.env['product.product'].create({
            'name': 'product_1',
            'uom_id': self.uom_unit_id,
            'lst_price': 15000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })
        product_2 = self.env['product.product'].create({
            'name': 'product_2',
            'uom_id': self.uom_unit_id,
            'lst_price': 21000,
            'taxes_id': [Command.link(self.default_tax.id)],
        })

        partner_line_id = self.report._get_generic_line_id(self.partner_b._name, self.partner_b.id)

        contract_1 = self.create_contract('contract_1', self.partner_b, 'sale')
        contract_2 = self.create_contract('contract_2', self.partner_b, 'sale')

        c1_sale_order_1 = self.create_sale_order(
            self.partner_b,
            [product_1, product_2],
            [1, 1],
            [15000.00, 21000.00],
            contract_1,
            date_order=event_date_01,
        )
        self.confirm_sale_order(c1_sale_order_1)
        self.deliver_sale_order(c1_sale_order_1)

        pay_1_l1 = self.create_contract_bank_statement_line(self.partner_b, 12000, contract=contract_1, sale_order=c1_sale_order_1, date=event_date_02)
        pay_1 = self.validate_statement_line(pay_1_l1)

        invoice_1 = self.invoicing_sale_order(c1_sale_order_1)
        self.post_invoice(invoice_1, invoice_date=event_date_03)

        c2_sale_order_2 = self.create_sale_order(
            self.partner_b,
            [product_1],
            [1],
            [18000.00],
            contract_2,
            date_order=event_date_02,
        )
        self.confirm_sale_order(c2_sale_order_2)
        self.deliver_sale_order(c2_sale_order_2)

        invoice_2 = self.invoicing_sale_order(c2_sale_order_2)
        self.post_invoice(invoice_2, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, self.date_test_start, self.date_test_end)

        # Check moves positions

        test_move_lines = (
            self.register_move_lines(pay_1) +
            self.register_move_lines(invoice_1) +
            self.register_move_lines(invoice_2)
        ).sorted(key=lambda rec: (rec.date, rec.id))

        self.check_moves_positions(
            {
                'unfold_all': True,
                'unfolded_lines': [],
                'tracking_first_event': 'by_contract',
            },
            test_move_lines,
            partner_line_id=partner_line_id,
        )

        # Check totals by contract

        contract_totals = [
            LineInfo(contract_1.id, None, None, None, None, None, 36000, 12000, 24000, 36000, 6000),
            LineInfo(contract_2.id, None, None, None, None, None, 18000, 0, 18000, 18000, 3000),
        ]

        self.check_totals_grouped({
                'unfold_all': False,
                'groupby_contract': True,
                'unfolded_lines': [partner_line_id],
                'tracking_first_event': 'by_contract',
            },
            contract_totals,
            self.AccountContract._name,
            partner_line_id=partner_line_id,
        )

        # All unfolded lines

        contract_1_id = self.report._get_generic_line_id(self.AccountContract._name, contract_1.id)
        contract_2_id = self.report._get_generic_line_id(self.AccountContract._name, contract_2.id)

        test_move_lines = (
            self.register_move_lines(pay_1) +
            self.register_move_lines(invoice_1) +
            self.register_move_lines(invoice_2)
        )

        lines_data = [
            LineInfo(
                partner_line_id,
                '',
                2,
                self.partner_b.name,
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, markup='total', parent_line_id=partner_line_id),
                partner_line_id,
                3,
                'Total ' + self.partner_b.name,
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
            LineInfo(
                contract_1_id,
                partner_line_id,
                3,
                contract_1.display_name,
                '',
                '',
                36000,
                12000,
                24000,
                36000,
                6000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[0].id, parent_line_id=contract_1_id),
                contract_1_id,
                3,
                test_move_lines[0].date.strftime('%m/%d/%Y'),
                test_move_lines[0].journal_id.code,
                '361000',
                0,
                12000,
                -12000,
                12000,
                2000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[1].id, parent_line_id=contract_1_id),
                contract_1_id,
                3,
                test_move_lines[1].date.strftime('%m/%d/%Y'),
                test_move_lines[1].journal_id.code,
                '361000',
                36000,
                0,
                24000,
                24000,
                4000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, parent_line_id=contract_1_id, markup='total'),
                contract_1_id,
                4,
                'Total ' + contract_1.display_name,
                '',
                '',
                36000,
                12000,
                24000,
                36000,
                6000,
            ),

            LineInfo(
                contract_2_id,
                partner_line_id,
                3,
                contract_2.display_name,
                '',
                '',
                18000,
                0,
                18000,
                18000,
                3000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[2].id, parent_line_id=contract_2_id),
                contract_2_id,
                3,
                test_move_lines[2].date.strftime('%m/%d/%Y'),
                test_move_lines[2].journal_id.code,
                '361000',
                18000,
                0,
                18000,
                18000,
                3000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, parent_line_id=contract_2_id, markup='total'),
                contract_2_id,
                4,
                'Total ' + contract_2.display_name,
                '',
                '',
                18000,
                0,
                18000,
                18000,
                3000,
            ),

            LineInfo(
                self.report._get_generic_line_id(None, None, markup='total'),
                '',
                1,
                'Total',
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
        ]

        self.check_all_lines(
            {
                'unfold_all': False,
                'groupby_contract': True,
                'unfolded_lines': [partner_line_id],
                'tracking_first_event': 'by_contract',
            },
            lines_data,
        )

    def test_orders_case1(self):
        event_date_01 = datetime.datetime(2023, 3, 1)
        event_date_02 = datetime.datetime(2023, 3, 2)
        event_date_03 = datetime.datetime(2023, 3, 3)

        product_1 = self.env['product.product'].create({
            'name': 'product_1',
            'uom_id': self.uom_unit_id,
            'lst_price': 15000,
        })
        product_2 = self.env['product.product'].create({
            'name': 'product_2',
            'uom_id': self.uom_unit_id,
            'lst_price': 21000,
        })

        partner_line_id = self.report._get_generic_line_id(self.partner_c._name, self.partner_c.id)

        sale_order_1 = self.create_sale_order(
            self.partner_c,
            [product_1, product_2],
            [1, 1],
            [15000.0, 21000.0],
            date_order=event_date_01,
        )
        self.confirm_sale_order(sale_order_1, date_order=event_date_01)

        pay_1_l1 = self.create_contract_bank_statement_line(self.partner_c, 12000, sale_order=sale_order_1, date=event_date_02)
        pay_1 = self.validate_statement_line(pay_1_l1)

        invoice_1 = self.invoicing_sale_order(sale_order_1)
        self.post_invoice(invoice_1, invoice_date=event_date_03)

        sale_order_2 = self.create_sale_order(
            self.partner_c,
            [product_1],
            [1],
            [18000.0],
            date_order=event_date_02,
        )
        self.confirm_sale_order(sale_order_2, date_order=event_date_02)

        invoice_2 = self.invoicing_sale_order(sale_order_2)
        self.post_invoice(invoice_2, invoice_date=event_date_02)

        self.generate_vat_documents(self.env.company.id, event_date_01, event_date_03)

        # Check moves positions

        test_move_lines = (
            self.register_move_lines(pay_1) +
            self.register_move_lines(invoice_1) +
            self.register_move_lines(invoice_2)
        ).sorted(key=lambda rec: (rec.date, rec.id))

        self.check_moves_positions(
            {
                'unfold_all': True,
                'unfolded_lines': [],
                'tracking_first_event': 'by_order',
            },
            test_move_lines,
            partner_line_id=partner_line_id,
        )

        # Check totals by orders

        contract_totals = [
            LineInfo(sale_order_1.id, None, None, None, None, None, 36000, 12000, 24000, 36000, 6000),
            LineInfo(sale_order_2.id, None, None, None, None, None, 18000, 0, 18000, 18000, 3000),
        ]

        self.check_totals_grouped(
            {
                'unfold_all': False,
                'groupby_sale_order': True,
                'unfolded_lines': [partner_line_id],
                'tracking_first_event': 'by_order',
            },
            contract_totals,
            self.SaleOrder._name,
            partner_line_id=partner_line_id,
        )

        # All unfolded lines

        order_1_line_id = self.report._get_generic_line_id(sale_order_1._name, sale_order_1.id)
        order_2_line_id = self.report._get_generic_line_id(sale_order_2._name, sale_order_2.id)

        test_move_lines = (
            self.register_move_lines(pay_1) +
            self.register_move_lines(invoice_1) +
            self.register_move_lines(invoice_2)
        )

        lines_data = [
            LineInfo(
                partner_line_id,
                '',
                2,
                self.partner_c.name,
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, markup='total', parent_line_id=partner_line_id),
                partner_line_id,
                3,
                'Total ' + self.partner_c.name,
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
            LineInfo(
                order_1_line_id,
                partner_line_id,
                3,
                sale_order_1.name,
                '',
                '',
                36000,
                12000,
                24000,
                36000,
                6000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[0].id, parent_line_id=order_1_line_id),
                order_1_line_id,
                3,
                test_move_lines[0].date.strftime('%m/%d/%Y'),
                test_move_lines[0].journal_id.code,
                '361000',
                0,
                12000,
                -12000,
                12000,
                2000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[1].id, parent_line_id=order_1_line_id),
                order_1_line_id,
                3,
                test_move_lines[1].date.strftime('%m/%d/%Y'),
                test_move_lines[1].journal_id.code,
                '361000',
                36000,
                0,
                24000,
                24000,
                4000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, parent_line_id=order_1_line_id, markup='total'),
                order_1_line_id,
                4,
                'Total ' + sale_order_1.name,
                '',
                '',
                36000,
                12000,
                24000,
                36000,
                6000,
            ),

            LineInfo(
                order_2_line_id,
                partner_line_id,
                3,
                sale_order_2.name,
                '',
                '',
                18000,
                0,
                18000,
                18000,
                3000,
            ),
            LineInfo(
                self.report._get_generic_line_id(self.AccountMoveLine._name, test_move_lines[2].id, parent_line_id=order_2_line_id),
                order_2_line_id,
                3,
                test_move_lines[2].date.strftime('%m/%d/%Y'),
                test_move_lines[2].journal_id.code,
                '361000',
                18000,
                0,
                18000,
                18000,
                3000,
            ),
            LineInfo(
                self.report._get_generic_line_id(None, None, parent_line_id=order_2_line_id, markup='total'),
                order_2_line_id,
                4,
                'Total ' + sale_order_2.name,
                '',
                '',
                18000,
                0,
                18000,
                18000,
                3000,
            ),

            LineInfo(
                self.report._get_generic_line_id(None, None, markup='total'),
                '',
                1,
                'Total',
                '',
                '',
                54000,
                12000,
                42000,
                54000,
                9000,
            ),
        ]

        self.check_all_lines(
            {
                'unfold_all': False,
                'groupby_sale_order': True,
                'unfolded_lines': [partner_line_id, order_1_line_id, order_2_line_id],
                'tracking_first_event': 'by_order',
            },
            lines_data,
        )

    def register_move_from_payment(self, partner, amount, payment_date):
        pay_line = self.create_bank_statement_line(partner=partner, amount=amount, date=payment_date)
        payment = self.validate_statement_line(pay_line)
        return payment.line_ids.filtered(
            lambda l: l.account_id.first_event and l.account_id.account_type == 'asset_receivable'
        )

    def register_move_from_invoice(self, partner, invoice_date, lines):
        invoice = self.create_invoice(
            partner=partner,
            products=[ln[0] for ln in lines],
            amounts=[ln[1] for ln in lines],
            taxes=[],
            date=invoice_date,
        )
        self.post_invoice(invoice, invoice_date=invoice_date)
        return invoice.line_ids.filtered(
            lambda l: l.account_id.first_event and l.account_id.account_type == 'asset_receivable'
        )

    def get_lines(self, options, partner_line_id, without_initials=True, without_totals=True):
        lines = self.report._get_lines(options)

        result_lines = []
        if lines:
            for line in lines:
                if line.get('parent_id') and line.get('parent_id').startswith(partner_line_id):
                    markup, record_model, record_id = self.report._parse_line_id(line.get('id'))[-1]
                    if (not without_initials or markup != 'initial') and (not without_totals or markup != 'total'):
                        result_lines.append(line)

        return result_lines

    def check_positions(self, lines, sequence):
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
                elif seq[0] == self.SaleOrder._name:
                    self.assertTrue(line.get('is_sale_order'))
                else:
                    self.assertEqual(line.get('caret_options'), seq[0])

                self.assertTrue(not markup)
                self.assertEqual(model, seq[0].split(':', 1)[0])
                self.assertEqual(record_id, seq[1])

    def check_move_lines(self, lines, move_lines, group_by_contract, parent_line_id=None):
        for i, line in enumerate(lines):
            move_line = move_lines[i]

            current_parent_line_id = parent_line_id
            if group_by_contract:
                current_parent_line_id = self.report._get_generic_line_id(
                    self.AccountContract._name,
                    move_line.contract_id and move_line.contract_id.id or None,
                    parent_line_id=current_parent_line_id,
                )

            self.assertEqual(line['id'], self.report._get_generic_line_id(move_line._name, move_line.id, parent_line_id=current_parent_line_id))
            self.assertEqual(line['level'], group_by_contract and 3 or 2)
            self.assertEqual(line['caret_options'], self.AccountMoveLine._name)
            self.assertIsNone(line.get('is_contract'))
            self.assertEqual(line['columns'][5]['no_format'], move_line.debit)
            self.assertEqual(line['columns'][6]['no_format'], move_line.credit)
            self.assertEqual(line['columns'][7]['no_format'], move_line.amount_currency)

    def check_moves_positions(self, default_options, move_lines, partner_line_id):
        options = TestAccountReportVATFirstEvent._generate_options(
            self.report,
            self.date_test_start,
            self.date_test_end,
            default_options=default_options,
        )

        lines = self.get_lines(options, partner_line_id)

        self.assertTrue(lines)

        self.check_positions(
            lines, [(r._name + self.get_move_line_menu_tag(r), r.id) for r in move_lines]
        )

    def check_totals_grouped(self, default_options, lines_data, group_type, partner_line_id):
        options = TestAccountReportVATFirstEvent._generate_options(
            self.report,
            self.date_test_start,
            self.date_test_end,
            default_options=default_options,
        )

        lines = self.get_lines(options, partner_line_id)

        self.assertTrue(lines)

        for i, line in enumerate(lines):
            line_id = self.report._get_generic_line_id(group_type, lines_data[i].id)
            self.assertEqual(line_id, line.get('id'))
            self.assertEqual(line['columns'][2]['no_format'], lines_data[i].debit)
            self.assertEqual(line['columns'][3]['no_format'], lines_data[i].credit)
            self.assertEqual(line['columns'][4]['no_format'], lines_data[i].balance)
            self.assertEqual(line['columns'][5]['no_format'], lines_data[i].first_event)
            self.assertEqual(line['columns'][6]['no_format'], lines_data[i].vat)

    def check_all_lines(self, default_options, lines_data):
        options = TestAccountReportVATFirstEvent._generate_options(
            self.report,
            self.date_test_start,
            self.date_test_end,
            default_options=default_options,
        )

        lines = self.report._get_lines(options)

        self.assertTrue(lines)

        for i, line in enumerate(lines):
            self.assertEqual(line['id'], lines_data[i].id)

            self.assertEqual(line.get('parent_id', ''), lines_data[i].parent_id)

            self.assertEqual(line['name'], lines_data[i].name)
            self.assertEqual(line['level'], lines_data[i].level)

            self.assertEqual(line['columns'][0]['no_format'] or '', lines_data[i].journal)
            self.assertEqual(line['columns'][1]['no_format'] or '', lines_data[i].account)
            self.assertEqual(line['columns'][2]['no_format'], lines_data[i].debit)
            self.assertEqual(line['columns'][3]['no_format'], lines_data[i].credit)
            self.assertEqual(line['columns'][4]['no_format'], lines_data[i].balance)
            self.assertEqual(line['columns'][5]['no_format'], lines_data[i].first_event)
            self.assertEqual(line['columns'][6]['no_format'], lines_data[i].vat)
