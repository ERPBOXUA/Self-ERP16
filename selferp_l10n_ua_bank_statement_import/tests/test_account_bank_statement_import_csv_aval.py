from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportCSVAval(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_csv_aval(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "Aval",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA493808050000000026000489999',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank Aval UAH',
            'code': 'BNK_AVAL_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA493808050000000026000489999',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_csv_aval').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'ТОВ "Новатор"',
            'company_registry': '38324141',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA303005280000026509455000255',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'ПРАТ "СК "БАО"',
            'company_registry': '33908383',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA143253650000002650001412254',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_aval.csv'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'text/csv',
                'name': 'test_aval.csv',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_aval.csv',
            'balance_start': 0.0,
            'balance_end': -5027.05,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,  # Index: 0
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 17436.57,
                'ref': 'BO20102558',
                'partner_name': 'ТОВ "Новатор"',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA303005280000026509455000255',
                'payment_ref': 'Переказ коштiв по платежам. прийнятим вiд населення за товари згiдно заяви про приеднання до умов договору на п.к. вiд 23.07.2020. з ПДВ',
            },
            {
                'sequence': 2,  # Index: 1
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 9815.00,
                'ref': '679',
                'partner_name': 'ПРЕДСТАВНИЦТВО "ЖЗ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA573005280000026007455078529',
                'payment_ref': 'За оклеювання вікон ударотривкою плівкою, зг. рф від 03/01/23 у т.ч. ПДВ 20% 1635.83 грн.',
            },
            {
                'sequence': 3,  # Index: 2
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2106.00,
                'ref': '6',
                'partner_name': 'ФОП ШЕВЧЕНКО ТАРАС ГРИГОРОВИЧ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA023052990000026000025023452',
                'payment_ref': 'Оплата за товар згідно рахунку від 11 січня 2023 р.без ПДВ',
            },
            {
                'sequence': 4,  # Index: 3
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -75630.00,
                'ref': '7',
                'partner_name': 'ТОВ "ЛПФ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA783052990000026000005035040',
                'payment_ref': 'Оплата за товар, згідно рахункам, в т. ч. ПДВ 20 % - 12 605,00 грн.',
            },
            {
                'sequence': 5,  # Index: 4
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 14760.00,
                'ref': '1830271',
                'partner_name': 'ПРАТ "СК "БАО"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA143253650000002650001412254',
                'payment_ref': 'Cтрах. виплата ТОВ "Фiрма "МД", вiд 10.01.2023р. зг. рах. вiд 05.01.2023р. в т.ч. ПДВ.',
            },
            {
                'sequence': 6,  # Index: 5
                'date': fields.Date.from_string('2023-01-12'),
                'amount': -12000.00,
                'ref': '6055',
                'partner_name': 'ТОВ "ВГ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA068999980385189000000173898',
                'payment_ref': '*;101;38382727; поповнення електронного рахунку з ПДВ;;;',
            },
            {
                'sequence': 7,  # Index: 6
                'date': fields.Date.from_string('2023-01-12'),
                'amount': 17377.08,
                'ref': 'BO20114451',
                'partner_name': 'ТОВ "Новатор"',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA303005280000026509455000255',
                'payment_ref': 'Переказ коштiв по платежам. прийнятим вiд населення за товари згiдно заяви про приеднання до умов договору на п.к. вiд 23.07.2020. з ПДВ',
            },
            {
                'sequence': 8,  # Index: 7
                'date': fields.Date.from_string('2023-01-12'),
                'amount': -1500.00,
                'ref': '6056',
                'partner_name': 'ТОВ "ВК"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA093510050000026002500589200',
                'payment_ref': 'Оплата доступу до інтернету згідно рах від 01/01/23р у т.ч. ПДВ 20% - 250.00 грн.',
            },
            {
                'sequence': 9,  # Index: 8
                'date': fields.Date.from_string('2023-01-12'),
                'amount': -3203.70,
                'ref': '6066',
                'partner_name': 'ТОВ "ЕПІК"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA383808050000000026005646984',
                'payment_ref': 'Оплата за товар, згідно рахунка від 11/01/23 ТОВ "ВГ", у т.ч. ПДВ 20% - 533.95 грн.',
            },
            {
                'sequence': 10,  # Index: 9
                'date': fields.Date.from_string('2023-01-12'),
                'amount': 10000.00,
                'ref': '9006',
                'partner_name': 'БУ ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA733515330000026008052228572',
                'payment_ref': 'Повернення гарантiйного платежу згiдно договору Без ПДВ.',
            },
            {
                'sequence': 11,  # Index: 10
                'date': fields.Date.from_string('2023-01-12'),
                'amount': 20024.00,
                'ref': '2058566',
                'partner_name': 'ПРАТ "СК "БАО"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA143253650000002650001412254',
                'payment_ref': 'Cтрах. виплата Бібіко Андрій Олександрович, вiд 12.01.2023р. зг. рах. вiд 11.01.2023р. в т.ч. ПДВ.',
            },
        ])

