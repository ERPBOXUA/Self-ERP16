from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportXLSUkrsib(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_xls_urksib(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "Ukrsib",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA243510050000026005879061779',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank Ukrsib UAH',
            'code': 'BNK_UKRSIB_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA243510050000026005879061779',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_xls_ukrsib').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'СТУС ВАСИЛЬ СЕМЕНОВИЧ',
            'company_registry': '2941125172',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA403510050000026009036443501',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'АТ "УКРСИББАНК"',
            'company_registry': '09807750',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA883510050000000006510300000',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_ukrsib.xls'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/vnd.ms-excel',
                'name': 'test_ukrsib.xls',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_ukrsib.xls',
            'balance_start': 0.0,
            'balance_end': -52873.86,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,      # Index: 0
                'date': fields.Date.from_string('2022-02-17'),
                'amount': 1000.00,
                'ref': '43',
                'partner_name': 'СТУС ВАСИЛЬ СЕМЕНОВИЧ',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA403510050000026009036443501',
                'payment_ref': '*zz00011467* Часткове повернення коштів, отриманих по пд. № 96 від 02.02.2022 р. згідно листа №1 від 12.02.2022 р. Без ПДВ.',
            },
            {
                'sequence': 2,      # Index: 1
                'date': fields.Date.from_string('2022-02-14'),
                'amount': -255027.00,
                'ref': '119',
                'partner_name': 'СТУС ВАСИЛЬ СЕМЕНОВИЧ',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA403510050000026009036443501',
                'payment_ref': 'Сплата за комп\'ютерні комплектуючі згідно рах.№ З-02002990 від 14.02.2022р., ПДВ не передбачено.',
            },
            {
                'sequence': 3,      # Index: 2
                'date': fields.Date.from_string('2022-02-08'),
                'amount': -4128.00,
                'ref': '112',
                'partner_name': 'ТЕЛІГА ОЛЕНА ІВАНІВНА ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA553052990000026004016714215',
                'payment_ref': 'Сплата за крісла офісні Special4You зг. рах. № 4 від 07.02.2022р., ПДВ не передбачено.',
            },
            {
                'sequence': 4,      # Index: 3
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -2000.00,
                'ref': '100',
                'partner_name': 'ДАТАГРУП ПрАТ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA543395000000026008148873009',
                'payment_ref': 'Сплата за телекомунікаційні послуги зг. дог. № 325594 від 01.06.2021р., у т.ч. ПДВ 20% - 333.33 грн.',
            },
            {
                'sequence': 5,      # Index: 4
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -1220.00,
                'ref': '102',
                'partner_name': 'СЛОБОДЯНИК ВІКТОРІЯ ВІКТОРІВНА ФОП ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA193138490000026008019405754',
                'payment_ref': 'Сплата за послуги доступу до мережі інтернет зг. дог.№ 0821-01 від 08.06.2021р., ПДВ непередбачено.',
            },
            {
                'sequence': 6,      # Index: 5
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -745.99,
                'ref': '108',
                'partner_name': 'ГУК Харків обл/МТГ Харкiв/11010100',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA818999980333119340000020649',
                'payment_ref': '*;101;43908842; ПДФО з з/п за 2у пол. 01.2022р.  Перерах. повністю термін 02.03.22р.;;;',
            },
            {
                'sequence': 7,      # Index: 6
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -911.78,
                'ref': '107',
                'partner_name': 'ГУ ДПС у Харківській області',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA508999980000355629201022040',
                'payment_ref': '*;101;43908842; Внески ЄСВ 22 % з з/п за 2у пол. 01.2022р. Перерах. повністю термін 02.03.22р.;;;',
            },
            {
                'sequence': 8,      # Index: 7
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -3.00,
                'ref': '1979499166',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 9,      # Index: 8
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -3.00,
                'ref': '1979499163',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 10,     # Index: 9
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -3.00,
                'ref': '1979499159',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 11,     # Index: 10
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -3.00,
                'ref': '1979499155',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 12,     # Index: 11
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -3.00,
                'ref': '1979499151',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 13,     # Index: 12
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -62.17,
                'ref': '109',
                'partner_name': 'ГУК Харків обл/МТГ Харкiв/11011000',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA188999980313070063000020001',
                'payment_ref': '*;101;43908842; Військовий збір 1,5% з з/п за 2у пол. 01.2022р. Перерах. повністю термін 02.03.22р;;;',
            },
            {
                'sequence': 14,     # Index: 13
                'date': fields.Date.from_string('2022-02-07'),
                'amount': -15202.50,
                'ref': '99',
                'partner_name': 'ВОРК ЕНД ЛАК ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA293510050000026003631412900',
                'payment_ref': 'Сплата за оренду нерухомого майна за 02.2022р. зг. дог. № 1/22/2 від 08.11.2021р., ПДВ не передбачено.',
            },
            {
                'sequence': 15,     # Index: 14
                'date': fields.Date.from_string('2022-02-04'),
                'amount': -40000.00,
                'ref': '103',
                'partner_name': 'МЕЛЬНИК АНДРІЙ АТАНАСОВИЧ ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA853220010000026005300045873',
                'payment_ref': 'Сплата за послуги розробки інтернет-сайту зг. дог. № ЕСТВ-1/22 від 03.01.2022р., ПДВ непередбачено.',
            },
            {
                'sequence': 16,     # Index: 15
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -3.00,
                'ref': '1978964743',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 17,     # Index: 16
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -3.00,
                'ref': '1978964742',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 18,     # Index: 17
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -24118.70,
                'ref': '94',
                'partner_name': 'ГІГА СТЕПАН ПЕТРОВИЧ ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA923510050000026006878983697',
                'payment_ref': 'Сплата за інжинірингові послуги зг. дог. №24-ДКС-21 від 10.12.2021р. та акту приймання-передачі № ДС-01/22 від 31.01.2022, ПДВ не передбачено',
            },
            {
                'sequence': 19,     # Index: 18
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -37566.10,
                'ref': '78',
                'partner_name': 'ІВАН ВАСИЛЬОВИЧ БОБУЛ ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA223510050000026007878947869',
                'payment_ref': 'Сплата за інжинірингові послуги зг. дог. №14-ДКС-21 від 08.10.2021р. та акту приймання-передачі № НБ-01/22 від 31.01.2022, ПДВ не передбачено',
            },
            {
                'sequence': 20,     # Index: 19
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -3.00,
                'ref': '1978867127',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 21,     # Index: 20
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -3.00,
                'ref': '1978867125',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435* UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 22,     # Index: 21
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -3.00,
                'ref': '1978867126',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA883510050000000006510300000',
                'payment_ref': 'Комісія по рах. UA2435*UAH за зовнішній платіж СЕП ССП зг.Дог. №03859 від 17.03.2021 без ПДВ',
            },
            {
                'sequence': 23,     # Index: 22
                'date': fields.Date.from_string('2022-02-02'),
                'amount': -2550.00,
                'ref': '92',
                'partner_name': 'СТУС ВАСИЛЬ СЕМЕНОВИЧ',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA403510050000026009036443501',
                'payment_ref': 'Сплата за лампи та стартери згідно рах.№ Р-01990732 від 01.02.2022р., ПДВ не передбачено.',
            },
            {
                'sequence': 24,     # Index: 23
                'date': fields.Date.from_string('2022-02-04'),
                'amount': 330680.42,
                'ref': '21184747',
                'partner_name': 'АТ "УКРСИББАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA333510050000000002900300005',
                'payment_ref': 'Гр.экв.продажу 11763.80 USD на МВР 04.02.22, ЗГІДНО ЗАЯВИ КЛІЄНТА № 8 .Курс 2811.0.Ком.банку 992.04.',
            },
            {
                'sequence': 25,     # Index: 24
                'date': fields.Date.from_string('2022-02-04'),
                'amount': -992.04,
                'ref': '3351603',
                'partner_name': 'АT УКРСИББАНК',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA773510050000000003739440005',
                'payment_ref': 'Списання комісії по рахунку UA6935* USD за продаж безготівкової іноземної валюти зг. Дог. №03859 від 17.03.2021 без ПДВ згідно заяви клієнта 8 .',
            },
       ])

