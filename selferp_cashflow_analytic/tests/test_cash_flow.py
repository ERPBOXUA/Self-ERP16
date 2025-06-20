from odoo import fields
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install')
class TestCashFlow(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super(TestCashFlow, cls).setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')

        cash_flow_analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Payment to suppliers plan',
            'cash_flow_article': True
        })
        cls.cash_flow_analytic_plan = cash_flow_analytic_plan

        analytic_account_c2 = cls.env['account.analytic.account'].create({
            'name': 'Payment to suppliers',
            'plan_id': cash_flow_analytic_plan.id
        })
        cls.analytic_account_c2 = analytic_account_c2

        analytic_account_c3 = cls.env['account.analytic.account'].create({
            'name': 'Payment for products',
            'plan_id': cash_flow_analytic_plan.id
        })
        cls.analytic_account_c3 = analytic_account_c3

        partner_c2 = cls.env['res.partner'].create({
            'name': 'Supplier 1',
            'is_company': True
        })
        cls.partner_c2 = partner_c2

        partner_c3 = cls.env['res.partner'].create({
            'name': 'Supplier 2',
            'is_company': True
        })
        cls.partner_c3 = partner_c3

        cls.payment_count = 0

    def _run_generic_test(self, partner_id, analytic_account_id, journal_id, amount):
        TestCashFlow.payment_count += 1
        statement_line = self.env['account.bank.statement.line'].create({
            'date': fields.Date.today(),
            'payment_ref': "Vendor payment %d" % TestCashFlow.payment_count,
            'partner_id': partner_id,
            'cash_flow_analytic_account_id': analytic_account_id,
            'amount': amount,
            'journal_id': journal_id,
        })

        entries = statement_line.move_id
        self.assertTrue(entries, "No journal entries were created")

        items = entries.line_ids
        self.assertTrue(items, "No journal items were created")

        analytic_line = items.mapped('analytic_line_ids')
        self.assertFalse(analytic_line, "Redundant analytic lines found")

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement_line.id).new({})
        wizard._action_trigger_matching_rules()
        self.assertEqual(wizard.state, 'valid', "Account bank statement line is invalid")

        wizard.button_validate(async_action=False)

        items = statement_line.move_id.line_ids
        self.assertTrue(items, "No journal items were created")

        bank_lines = items.filtered(lambda l: l.account_id.account_type == 'asset_cash')
        self.assertEqual(len(bank_lines), 1, "No move lines of appropriate bank type")

        self.assertEqual(bank_lines.cash_flow_analytic_account_id.id, analytic_account_id, "No Cash Flow account is set")

        analytic_line = bank_lines.analytic_line_ids.filtered(lambda l: l.account_id.id == analytic_account_id)
        self.assertEqual(len(analytic_line), 1, "No valid analytic lines")

        self.assertEqual(float_compare(analytic_line.amount, amount, precision_digits=2), 0, "Amount must be %.2f !!!" % amount)

    def test_case2(self):
        journal = self.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', self.env.company.id)], limit=1
        )
        self.assertEqual(len(journal), 1, "No appropriate journal found")

        self.assertTrue(journal.suspense_account_id, "Suspense account is not set for 'Bank' journal")

        self.assertTrue(self.analytic_account_c2, "Cannot find analytic account")

        self._run_generic_test(self.partner_c2.id, self.analytic_account_c2.id, journal.id, -500)

    def test_case3(self):
        journal = self.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', self.env.company.id)], limit=1
        )
        self.assertTrue(journal, "No appropriate journal found")

        self.assertTrue(journal.suspense_account_id, "Suspense account is not set for 'Bank' journal")

        self.assertTrue(self.analytic_account_c3, "Cannot find analytic account")

        self._run_generic_test(self.partner_c3.id, self.analytic_account_c3.id, journal.id, 700)
