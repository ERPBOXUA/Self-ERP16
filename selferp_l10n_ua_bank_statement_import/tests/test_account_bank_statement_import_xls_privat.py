from odoo import fields
from odoo.tools import file_open
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBankStatementImportXLSPrivat(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_import_xls_privat(self):
        #
        # Create journal
        #
        bank = self.env['res.bank'].create({
            'name': "Privat",
        })

        self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': self.env.user.company_id.partner_id.id,
            'acc_number': 'UA123456789012345678901234567',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank Privat UAH',
            'code': 'BNK_PRIVAT_UAH',
            'type': 'bank',
            'bank_id': bank.id,
            'bank_acc_number': 'UA123456789012345678901234567',
            'currency_id': self.env.ref('base.UAH').id,
            'bank_statements_source': 'file_import',
            'import_mapping_id': self.env.ref('selferp_l10n_ua_bank_statement_import.account_bank_statement_import_xls_privat').id,
        })

        #
        # Create partners
        #
        partner1 = self.env['res.partner'].create({
            'name': 'Partner UAH',
            'company_registry': '12345678',
        })
        partner_bank1 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner1.id,
            'acc_number': 'UA573052990000029244840015000',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'БАНДЕРА С.А. ФОП',
            'company_registry': '3249312549',
        })
        partner_bank2 = self.env['res.partner.bank'].create({
            'bank_id': bank.id,
            'partner_id': partner2.id,
            'acc_number': 'UA413052990000026006030112136',
        })

        #
        # Use an import wizard to process the file
        #
        file_path = 'selferp_l10n_ua_bank_statement_import/tests/testfiles/test_privat.xls'
        with file_open(file_path, 'rb') as f:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/vnd.ms-excel',
                'name': 'test_privat.xls',
                'raw': f.read(),
            }).ids)

        #
        # Check the imported bank statement
        #
        imported_statement = self.env['account.bank.statement'].search([
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_privat.xls',
            'balance_start': 0.0,
            'balance_end': -108990.42,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda r: r.sequence), [
            {
                'sequence': 1,      # Index: 0
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -3500.00,
                'ref': 'SAMBMCUC00NAT4.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 2,      # Index: 1
                'date': fields.Date.from_string('2022-12-30'),
                'amount': 3900.00,
                'ref': 'JBKLMCUO6W81VR.P',
                'partner_name': 'БАНДЕРА С.А. ФОП',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA413052990000026006030112136',
                'payment_ref': 'ОПЛАТА ПОСЛУГ РАХУНОК ВIД 30.12.2022 РОКУ Без ПДВ.',
            },
            {
                'sequence': 3,      # Index: 2
                'date': fields.Date.from_string('2022-12-30'),
                'amount': -2300.00,
                'ref': 'SAMBMCVC08E44R.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 4,      # Index: 3
                'date': fields.Date.from_string('2022-12-28'),
                'amount': -5000.00,
                'ref': 'SAMBMCSC0E7YRY.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 5,      # Index: 4
                'date': fields.Date.from_string('2022-12-28'),
                'amount': -5000.00,
                'ref': 'COIEM1228X2KQU.1',
                'partner_name': 'розрахунки за картами (С+, ACQ2)',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA073052990000029245827503642',
                'payment_ref': '4246 **** **** 7558 28.12.2022 15:36:06 Зняття готiвки: Банкомат Вiддiлення банку',
            },
            {
                'sequence': 6,      # Index: 5
                'date': fields.Date.from_string('2022-12-28'),
                'amount': -50.00,
                'ref': 'COIEM1228X2KQX.1',
                'partner_name': 'Выдача наличных, пополнение, P2P',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA263052990000065104908015712',
                'payment_ref': 'Еквайрингова комiсiя без ПДВ 28.12.2022 15:36:06 по картцi 4246 **** **** 7558',
            },
            {
                'sequence': 7,      # Index: 6
                'date': fields.Date.from_string('2022-12-27'),
                'amount': -80.00,
                'ref': 'COIEM1227G1E2S.1',
                'partner_name': 'Выдача наличных, пополнение, P2P',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA263052990000065104908015712',
                'payment_ref': 'Еквайрингова комiсiя без ПДВ 27.12.2022 08:26:49 по картцi 4246 **** **** 7558',
            },
            {
                'sequence': 8,      # Index: 7
                'date': fields.Date.from_string('2022-12-27'),
                'amount': -8000.00,
                'ref': 'COIEM1227G1E4M.1',
                'partner_name': 'розрахунки за картами (С+, ACQ2)',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA073052990000029245827503642',
                'payment_ref': '4246 **** **** 7558 27.12.2022 08:26:49 Зняття готiвки: Банкомат Еко-маркет',
            },
            {
                'sequence': 9,      # Index: 8
                'date': fields.Date.from_string('2022-12-25'),
                'amount': -4000.00,
                'ref': 'SAMBMCPC0FSSID.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 10,     # Index: 9
                'date': fields.Date.from_string('2022-12-23'),
                'amount': -809.42,
                'ref': 'COIEM12235UL1J.1',
                'partner_name': 'розрахунки за картами (С+, ACQ1) карти ПБ',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA893052990000029247827503747',
                'payment_ref': '4246 **** **** 7558 23.12.2022 10:28:24 Подорожi',
            },
            {
                'sequence': 11,     # Index: 10
                'date': fields.Date.from_string('2022-12-21'),
                'amount': -5100.00,
                'ref': 'COIEM1221NSQHI.1',
                'partner_name': 'розрахунки за картами (С+, ACQ2)',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA073052990000029245827503642',
                'payment_ref': '4246 **** **** 7558 20.12.2022 18:56:40 Зняття готiвки: Банкомат Метроград',
            },
            {
                'sequence': 12,     # Index: 11
                'date': fields.Date.from_string('2022-12-21'),
                'amount': -51.00,
                'ref': 'COIEM1221NSQHN.1',
                'partner_name': 'Выдача наличных, пополнение, P2P',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA263052990000065104908015712',
                'payment_ref': 'Еквайрингова комiсiя без ПДВ 20.12.2022 18:56:40 по картцi 4246 **** **** 7558',
            },
            {
                'sequence': 13,     # Index: 12
                'date': fields.Date.from_string('2022-12-20'),
                'amount': -30000.00,
                'ref': 'SAMBMCKC0XOHNG.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 14,     # Index: 13
                'date': fields.Date.from_string('2022-12-17'),
                'amount': -15000.00,
                'ref': 'SAMBMCHC05ITIS.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 15,     # Index: 14
                'date': fields.Date.from_string('2022-12-16'),
                'amount': -10000.00,
                'ref': 'COIEM12168PR8I.1',
                'partner_name': 'розрахунки за картами (С+, ACQ2)',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA073052990000029245827503642',
                'payment_ref': '4246 **** **** 7558 16.12.2022 08:23:15 Зняття готiвки: Банкомат Еко-маркет',
            },
            {
                'sequence': 16,     # Index: 15
                'date': fields.Date.from_string('2022-12-16'),
                'amount': -100.00,
                'ref': 'COIEM12168PR8J.1',
                'partner_name': 'Выдача наличных, пополнение, P2P',
                'partner_id': partner1.id,
                # 'partner_bank_id': None,  # partner_bank1 will be got here as a computed value...
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA263052990000065104908015712',
                'payment_ref': 'Еквайрингова комiсiя без ПДВ 16.12.2022 08:23:15 по картцi 4246 **** **** 7558',
            },
            {
                'sequence': 17,     # Index: 16
                'date': fields.Date.from_string('2022-12-15'),
                'amount': -5000.00,
                'ref': 'HSACM1215L01CR.1',
                'partner_name': 'Текущий депозит ШЕВЧЕНКО Т.Г. ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA163052990000026007046218335',
                'payment_ref': 'Перерахування коштiв на депозит згiдно з вiдкритою офертою банку',
            },
            {
                'sequence': 18,     # Index: 17
                'date': fields.Date.from_string('2022-12-15'),
                'amount': -17000.00,
                'ref': 'SAMBMCFC0LEY62.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 19,     # Index: 18
                'date': fields.Date.from_string('2022-12-15'),
                'amount': 10000.00,
                'ref': 'HSKLM1215L65VZ.P',
                'partner_name': 'ТОВ "РОГИ-КОПИТА"',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA933006140000026005500384605',
                'payment_ref': 'Оплата за наданi послуги згiдно акту б/н вiд  30/11/22, без ПДВБез ПДВ',
            },
            {
                'sequence': 20,     # Index: 19
                'date': fields.Date.from_string('2022-12-12'),
                'amount': -4000.00,
                'ref': 'SAMBMCCC0N226X.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 21,     # Index: 20
                'date': fields.Date.from_string('2022-12-12'),
                'amount': 4000.00,
                'ref': 'JBKLMCCO6T936T.P',
                'partner_name': 'МОЯ ІГРАШКА ТОВ',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA263052990000026006010104216',
                'payment_ref': 'Згiдно рахунку на оплату вiд 10.12,2022 р.',
            },
            {
                'sequence': 22,     # Index: 21
                'date': fields.Date.from_string('2022-12-09'),
                'amount': -5000.00,
                'ref': 'SAMBMC9C0YFICV.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 23,     # Index: 22
                'date': fields.Date.from_string('2022-12-08'),
                'amount': -3900.00,
                'ref': 'SAMBMC8C0HQ9XE.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 24,     # Index: 23
                'date': fields.Date.from_string('2022-12-07'),
                'amount': 2700.00,
                'ref': 'JBKLMC7O6STQV0.P',
                'partner_name': 'ГРУШЕВСЬКИЙ М.С. ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA333052990000026002041706632',
                'payment_ref': 'оплата послуг за листопад  рахункок вiд 06.12,2022 р.Без ПДВ.',
            },
            {
                'sequence': 25,     # Index: 24
                'date': fields.Date.from_string('2022-12-07'),
                'amount': 1200.00,
                'ref': 'JBKLMC7O6SNBXE.P',
                'partner_name': 'ФРАНКО І.Я. ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA383052990000026004006228142',
                'payment_ref': 'Оплата за бух послуги зг. рах. вiд 06.12.2022 р.',
            },
            {
                'sequence': 26,     # Index: 25
                'date': fields.Date.from_string('2022-12-06'),
                'amount': -3300.00,
                'ref': 'SAMBMC6C04PJXL.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 27,     # Index: 26
                'date': fields.Date.from_string('2022-12-06'),
                'amount': 3300.00,
                'ref': 'JBKLMC6O6SMA9O.P',
                'partner_name': 'БАНДЕРА С.А. ФОП',
                'partner_id': partner2.id,
                'partner_bank_id': partner_bank2.id,
                'account_number': 'UA413052990000026006030112136',
                'payment_ref': 'ОПЛАТА ПОСЛУГ РАХУНОК ВIД 06.12.2022 РОКУ БЕЗ ПДВ.',
            },
            {
                'sequence': 28,     # Index: 27
                'date': fields.Date.from_string('2022-12-01'),
                'amount': -5000.00,
                'ref': 'SAMBMC1C0WPVUU.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 29,     # Index: 28
                'date': fields.Date.from_string('2022-12-01'),
                'amount': -4900.00,
                'ref': 'SAMBMC1C0SX65D.1',
                'partner_name': 'UAH Тр.рахунок',
                'partner_id': partner1.id,
                'partner_bank_id': partner_bank1.id,
                'account_number': 'UA573052990000029244840015000',
                'payment_ref': 'Переказ власних коштiв.',
            },
            {
                'sequence': 30,     # Index: 29
                'date': fields.Date.from_string('2022-12-01'),
                'amount': 3000.00,
                'ref': 'JBKLMC1O6RVD7D.P',
                'partner_name': 'КОТЛЯРЕВСЬКИЙ І.П. ФОП',
                'partner_id': None,
                'partner_bank_id': None,
                'account_number': 'UA343052990000026005000118053',
                'payment_ref': 'сплата за послуги ДОГОВIР вiд 03.07.2020р., згiдно рахунка вiд 01.12.2022р. Без ПДВ.',
            },
       ])

