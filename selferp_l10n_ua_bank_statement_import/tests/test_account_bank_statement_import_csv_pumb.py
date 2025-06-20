from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportCSVPUMB(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_csv_pumb(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "PUMB",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA623348510000000000260087146',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank PUMB UAH',
            'code': 'BNK_PUMB_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA623348510000000000260087146',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_csv_pumb').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'Головне управління ДПС у м. Києві',
            'company_registry': '44116011',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA678999980000355659201022654',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'ГОЛОВНЕ УДКСУ У М.КИЄВІ',
            'company_registry': '37993783',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA718999980313090063000026001',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_pumb.csv'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'text/csv',
                'name': 'test_pumb.csv',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_pumb.csv',
            'balance_start': 0.0,
            'balance_end': 6486.00,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,  # Index: 0
                'date': fields.Date.from_string('2022-12-12'),
                'amount': -3670.00,
                'ref': '63',
                'partner_name': 'ПВНЗ "МІТ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA473808050000000026003162846',
                'payment_ref': 'Оплата за освітні послуги згідно рах. від 01.12.2022, ШЕВЧЕНКО Т.Г., без ПДВ',
            },
            {
                'sequence': 2,  # Index: 1
                'date': fields.Date.from_string('2022-12-12'),
                'amount': 3500.00,
                'ref': '@2PL999390',
                'partner_name': 'Транз.рах._ DN, DG, DZ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA293052990000029023866100110',
                'payment_ref': 'Повернення поворотньої фiнансової допомоги, Шевченко Тарас Григорович',
            },
            {
                'sequence': 3,  # Index: 2
                'date': fields.Date.from_string('2022-12-20'),
                'amount': -603.00,
                'ref': '65',
                'partner_name': 'ГУК у м.Києві/Оболон.р-н/11010100',
                # 'partner_id': None,
                # 'partner_bank_id': None,
                'partner_id': partner2.id,              # get by same KOR_OKPO
                'partner_bank_id': partner_bank2.id,    # get by partner_id
                'account_number': 'UA868999980333109340000026006',
                'payment_ref': '*";"101";"Податок з доходів найманих працівників с зп за 1 пол грудня 2022 р.";"";"";", без ПДВ',
            },
            {
                'sequence': 4,  # Index: 3
                'date': fields.Date.from_string('2022-12-20'),
                'amount': -737.00,
                'ref': '67',
                'partner_name': 'Головне управління ДПС у м. Києві',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA678999980000355659201022654',
                'payment_ref': '*";"101";" ЄСВ за виплату зп за 1-шу пол грудня 2022 р,";"";"";", без ПДВ',
            },
            {
                'sequence': 5,  # Index: 4
                'date': fields.Date.from_string('2022-12-20'),
                'amount': -50.25,
                'ref': '66',
                'partner_name': 'ГОЛОВНЕ УДКСУ У М.КИЄВІ',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA718999980313090063000026001',
                'payment_ref': '101";"Війсковий збір с зп за 1-шу пол грудня 2022 р,";"";"";", без ПДВ',
            },
            {
                'sequence': 6,  # Index: 5
                'date': fields.Date.from_string('2022-12-20'),
                'amount': -2696.75,
                'ref': '64',
                'partner_name': 'Бандера С.А.',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA473220010000026207312976385',
                'payment_ref': 'Бандера С.А. Виплата ЗП за 1-пол грудня 2022 р. ";"";"";", без ПДВ',
            },
            {
                'sequence': 7,  # Index: 6
                'date': fields.Date.from_string('2022-12-20'),
                'amount': 3000.00,
                'ref': '@2PL480198',
                'partner_name': 'Транз.рах._ DN, DG, DZ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA293052990000029023866100110',
                'payment_ref': 'Повернення поворотньої фiнансової допомоги, Шевченко Тарас Григорович',
            },
            {
                'sequence': 8,  # Index: 7
                'date': fields.Date.from_string('2022-12-29'),
                'amount': 12000.00,
                'ref': '658',
                'partner_name': 'НП ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA063052990000026004021702546',
                'payment_ref': 'Оплата згiдно рахунку вiд 03.08.2022 у сумi 12000.00',
            },
            {
                'sequence': 9,  # Index: 8
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -603.00,
                'ref': '69',
                'partner_name': 'ГУК у м.Києві/Оболон.р-н/11010100',
                # 'partner_id': None,
                # 'partner_bank_id': None,
                'partner_id': partner2.id,              # get by same KOR_OKPO
                'partner_bank_id': partner_bank2.id,    # get by partner_id
                'account_number': 'UA868999980333109340000026006',
                'payment_ref': '*";"101";"Податок з доходів найманих працівників с зп за 2 пол грудня 2022 р.";"";"";", без ПДВ',
            },
            {
                'sequence': 10,  # Index: 9
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -737.00,
                'ref': '70',
                'partner_name': 'Головне управління ДПС у м. Києві',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA678999980000355659201022654',
                'payment_ref': '*";"101";" ЄСВ за виплату зп за 2-гу пол грудня 2022 р,";"";"";", без ПДВ',
            },
            {
                'sequence': 11,  # Index: 10
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -50.25,
                'ref': '71',
                'partner_name': 'ГОЛОВНЕ УДКСУ У М.КИЄВІ',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA718999980313090063000026001',
                'payment_ref': '101";"Війсковий збір с зп за 2-гу пол грудня 2022 р,";"";"";", без ПДВ',
            },
            {
                'sequence': 12,  # Index: 11
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -2696.75,
                'ref': '68',
                'partner_name': 'Бандера С.А.',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA473220010000026207312976385',
                'payment_ref': 'Бандера С.А. Виплата ЗП за 2-пол грудня 2022 р. ";"";"";", без ПДВ',
            },
            {
                'sequence': 13,  # Index: 12
                'date': fields.Date.from_string('2022-12-31'),
                'amount': -170.00,
                'ref': '.21151059.152969.359',
                'partner_name': 'ТОВ "КОЗАК"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA463348510000035703111706393',
                'payment_ref': 'Договірне списання комісії за тарифним  пакетом за період з 01/12/2022 по 31/12/2022, від 24/03/2017 зг-но Тарифів ПУМБ',
            },
        ])

