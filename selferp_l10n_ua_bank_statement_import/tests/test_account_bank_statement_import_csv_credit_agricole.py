from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportCSVCreditAgricole(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_csv_credit_agricole(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "Credit Agricole",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA933006140000026005500384605',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank Credit Agricole UAH',
            'code': 'BNK_CA_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA933006140000026005500384605',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_csv_credit_agricole').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'ТОВ СЕЛФ-ЕРП',
            'company_registry': '44112750',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA513006140000035709000423654',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'ТОВ БСМ',
            'company_registry': '35286792',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA473006140000026001500091174',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_credit_agricole.csv'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'text/csv',
                'name': 'test_credit_agricole.csv',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_credit_agricole.csv',
            'balance_start': 0.0,
            'balance_end': 429855.54,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,  # Index: 0
                'date': fields.Date.from_string('2023-01-12'),
                'amount': 164700.00,
                'ref': '2249',
                'partner_name': 'ТОВ Софтсерв-МТ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA493253650000002600801443037',
                'payment_ref': 'Оплата за передпроектне дослідження та бізнес-аналіз процесі',
            },
            {
                'sequence': 2,  # Index: 1
                'date': fields.Date.from_string('2023-01-13'),
                'amount': 275770.20,
                'ref': '3276746/2',
                'partner_name': 'АТ КРЕДІ АГРІКОЛЬ БАНК',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA573006140000028005840000001',
                'payment_ref': 'ЗАРАХ. ГРН. ВІД ПРОДАЖУ ВАЛ. 7500 USD КУРС 36.88 ТОРГИ 13.01',
            },
            {
                'sequence': 3,  # Index: 2
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '12',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 4,  # Index: 3
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '11',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 5,  # Index: 4
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '13',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 6,  # Index: 5
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '6',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 7,  # Index: 6
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '4',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 8,  # Index: 7
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '5',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 9,  # Index: 8
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '3',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 10,  # Index: 9
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '16',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 11,  # Index: 10
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.50,
                'ref': '15',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 12,  # Index: 11
                'date': fields.Date.from_string('2023-01-13'),
                'amount': -2.50,
                'ref': '10',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 13,  # Index: 12
                'date': fields.Date.from_string('2023-01-13'),
                'amount': -2.50,
                'ref': '7',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 14,  # Index: 13
                'date': fields.Date.from_string('2023-01-13'),
                'amount': -2.50,
                'ref': '18',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 15,  # Index: 14
                'date': fields.Date.from_string('2023-01-13'),
                'amount': -12.00,
                'ref': '9',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 16,  # Index: 15
                'date': fields.Date.from_string('2023-01-13'),
                'amount': -12.00,
                'ref': '17',
                'partner_name': 'ТОВ СЕЛФ-ЕРП',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA513006140000035709000423654',
                'payment_ref': 'Сплата комісії банку Перекази в нац. валюті в інший банк в',
            },
            {
                'sequence': 17,  # Index: 16
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -30.00,
                'ref': '12',
                'partner_name': 'ГУК Львiв/Львiвська тг/11011000',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA288999980313090063000013001',
                'payment_ref': '|101|44112750 |Вiйськовий збiр з з заробiтної плати 12/22Без',
            },
            {
                'sequence': 18,  # Index: 17
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -30.00,
                'ref': '4',
                'partner_name': 'ГУК Львiв/Львiвська тг/11011000',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA288999980313090063000013001',
                'payment_ref': '|101|44112750 |Вiйськовий збiр з з заробiтної плати 12/22Без',
            },
            {
                'sequence': 19,  # Index: 18
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -302.00,
                'ref': '3',
                'partner_name': 'ГУК Львiв/Львiвська тг/11010100',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA528999980333159340000013933',
                'payment_ref': '|101|44112750 |ПДФО з з заробiтної плати 12/22Без ПДВ',
            },
            {
                'sequence': 20,  # Index: 19
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -365.00,
                'ref': '13',
                'partner_name': 'Головне управлiння ДПС у Львiвськiй об',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA728999980000355699201021301',
                'payment_ref': '|101|44112750 |ЄСВ  з з заробітної плати 12/22, без ПДВБез П',
            },
            {
                'sequence': 21,  # Index: 20
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -500.00,
                'ref': '11',
                'partner_name': 'ГУК Львiв/Львiвська тг/11010100',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA528999980333159340000013933',
                'payment_ref': '|101|44112750 |ПДФО з з заробiтної плати 12/22Без ПДВ',
            },
            {
                'sequence': 22,  # Index: 21
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -521.80,
                'ref': '5',
                'partner_name': 'Головне управлiння ДПС у Львiвськiй об',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA728999980000355699201021301',
                'payment_ref': '|101|44112750 |ЄСВ  з з заробітної плати 12/22, без ПДВБез П',
            },
            {
                'sequence': 23,  # Index: 22
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -1000.00,
                'ref': '6',
                'partner_name': 'ГОЛОВНЕ УДКСУ У ЛЬВIВСЬКIЙ ОБЛАСТI',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA618999980314040698000013933',
                'payment_ref': '*|101|44112750 |сплата єдиного податку 2022 р.',
            },
            {
                'sequence': 24,  # Index: 23
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -7811.86,
                'ref': '2',
                'partner_name': 'ТОВ БСМ',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA473006140000026001500091174',
                'payment_ref': 'Оплата за оренду примiщення за грудень 2022 ,без ПДВБез ПДВ',
            },
        ])

