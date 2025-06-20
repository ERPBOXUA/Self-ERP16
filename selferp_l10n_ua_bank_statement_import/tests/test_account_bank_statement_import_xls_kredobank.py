from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportXLSKredobank(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_xls_kredobank(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "KredoBank",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA44325*',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank KredoBank UAH',
            'code': 'BNK_KREDO_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA44325*',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_xls_kredobank').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'Львівська міська ТГ',
            'company_registry': '38008294',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA288999980313090063000013001',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'АТ "КРЕДОБАНК"',
            'company_registry': '0980786',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA933253650000000000651001001',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_kredobank.xls'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/vnd.ms-excel',
                'name': 'test_kredobank.xls',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_kredobank.xls',
            'balance_start': 0.0,
            'balance_end': 30025.83,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,      # Index: 0
                'date': fields.Date.from_string('2023-01-02'),
                'amount': 2186.32,
                'ref': '26288',
                'partner_name': 'ПрАТ "Фіалка"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA803510050000026045283376300',
                'payment_ref': 'Повернення помилково перерахованих коштів ПД № 2 від 30.12.2022 р., у т.ч. ПДВ 20% - 364.39 грн.',
            },
            {
                'sequence': 2,      # Index: 1
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 5000.00,
                'ref': '2246',
                'partner_name': 'ТОВ "Комфорт плюс"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA493253650000002600801443037',
                'payment_ref': 'Членський внесок за 1 квартал 2023 р., без ПДВ.',
            },
            {
                'sequence': 3,      # Index: 2
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 8000.00,
                'ref': '1692',
                'partner_name': 'ТОВ "Квітка України"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA833005280000026004455082819',
                'payment_ref': 'Членський внесок за 1 квартал 2023р.',
            },
            {
                'sequence': 4,      # Index: 3
                'date': fields.Date.from_string('2023-01-11'),
                'amount': 13000.00,
                'ref': '2',
                'partner_name': 'ТОВ "Філадельфія"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA183006140000026007500319151',
                'payment_ref': 'Членський внесок',
            },
            {
                'sequence': 5,      # Index: 4
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -4471.89,
                'ref': '239',
                'partner_name': 'ПРАТ Львівський проектний інститут',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA413510050000026000283376301',
                'payment_ref': 'Оплата за оренду приміщення згідно договору оренди N-O від 01/1/22 р. в тч ПДВ 20% 745.32 грн.',
            },
            {
                'sequence': 6,      # Index: 5
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -3.00,
                'ref': '2028437',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 7,      # Index: 6
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -12166.84,
                'ref': '238',
                'partner_name': 'ТОВ "Мамина світлиця"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA473006140000026001500091174',
                'payment_ref': 'Оплата за оренду приміщення згідно договору оренди приміщення 03/22 БО від 31/12/20 р. в тч ПДВ 20% 1861.14 грн.',
            },
            {
                'sequence': 8,      # Index: 7
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -305.00,
                'ref': '242',
                'partner_name': 'Львіська міська ТГ',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA528999980333159340000013933',
                'payment_ref': '*;101;43287455 ;Податок з доходiв фiзичних осiб з заробітної плати; ; ; ;  01/23, без ПДВ.',
            },
            {
                'sequence': 9,      # Index: 8
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.00,
                'ref': '2028441',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 10,     # Index: 9
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -26.00,
                'ref': '243',
                'partner_name': 'Львівська міська ТГ',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA288999980313090063000013001',
                'payment_ref': '*;11011000;43287455;Військовий збір з заробітної плати за 01/23 р., без ПДВ;;;',
            },
            {
                'sequence': 11,     # Index: 10
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.00,
                'ref': '2028438',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 12,     # Index: 11
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -540.00,
                'ref': '241',
                'partner_name': 'ГУ ДПС У ЛЬВIВ. ОБЛ., ФРАНК.Р-Н',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA728999980000355699201021301',
                'payment_ref': '*;101;43287455;Єдиний соцiальний внесок 22 % з  заробітної плати 01/23   без ПДВ;;;',
            },
            {
                'sequence': 13,     # Index: 12
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.00,
                'ref': '2028440',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 14,     # Index: 13
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2.00,
                'ref': '2028442',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 15,     # Index: 14
                'date': fields.Date.from_string('2023-01-11'),
                'amount': -2348.38,
                'ref': '240',
                'partner_name': 'Квітень Орися Мирославівня',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA783253650000026209021751343',
                'payment_ref': 'Перерахування заробітної плати 01/23 без ПДВ, податки сплачені повністю 10/01/23 р., без ПДВ.',
            },
            {
                'sequence': 16,     # Index: 15
                'date': fields.Date.from_string('2023-01-16'),
                'amount': -3810.00,
                'ref': '244',
                'partner_name': 'ТОВ "ІНТЕРНЕТ СІТІ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA373005280000026008455006299',
                'payment_ref': 'Оплата за домент по рах СФ-00011650 від 14/01/2023 р. в т ч ПДВ - 585,00 грн.',
            },
            {
                'sequence': 17,     # Index: 16
                'date': fields.Date.from_string('2023-01-16'),
                'amount': -2.00,
                'ref': '2465493',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 18,     # Index: 17
                'date': fields.Date.from_string('2023-01-23'),
                'amount': -2.00,
                'ref': '3674362',
                'partner_name': 'АТ "КРЕДОБАНК"',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA933253650000000000651001001',
                'payment_ref': 'Комісія за переказ коштів за межі Банку на ел.носіях',
            },
            {
                'sequence': 19,     # Index: 18
                'date': fields.Date.from_string('2023-01-23'),
                'amount': -1477.38,
                'ref': '1',
                'partner_name': 'ТОВ "Девелоп УкраїНА"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA923515330000026000052116370',
                'payment_ref': 'Оплата за послуги з посередництва згідно рахунку №59363 від 23.01.23 Без ПДВ',
            },
            {
                'sequence': 20,     # Index: 19
                'date': fields.Date.from_string('2023-01-24'),
                'amount': 9000.00,
                'ref': '85',
                'partner_name': 'ТОВ "НІЧНІ СИСТЕМИ"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA533348510000000026000176961',
                'payment_ref': 'Оплата за послуги зг.рах.№23/01/2023/Р-01 від 23.01.23 р.,',
            },
            {
                'sequence': 21,     # Index: 20
                'date': fields.Date.from_string('2023-01-25'),
                'amount': 9000.00,
                'ref': '155489047',
                'partner_name': 'Матвієнко Ніна Митрофанівна',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA273348510000026206114399440',
                'payment_ref': 'Оплата за послуги згідно договору v24/01/2021',
            },
            {
                'sequence': 22,     # Index: 21
                'date': fields.Date.from_string('2023-01-25'),
                'amount': 9000.00,
                'ref': '803',
                'partner_name': 'ВОВ ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA973052990000026002026204201',
                'payment_ref': 'Iнформацiйно-консультацiйнi послуги з питань iнформатизацiї згiдно Договiру № 2/01/2023/Р-5. Без ПДВ.',
            },
       ])

