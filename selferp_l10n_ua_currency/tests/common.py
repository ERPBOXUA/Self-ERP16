from datetime import date

from odoo.tests import tagged

from odoo.addons.selferp_l10n_ua_ext.tests.common import AccountTestCommon


@tagged('post_install', '-at_install')
class TestCurrencyCommon(AccountTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_usd = cls.env.ref('base.USD')
        cls.currency_usd.action_unarchive()

        cls.currency_uah = cls.env.ref('base.UAH')
        cls.currency_uah.action_unarchive()

        cls.company = cls.setup_company_data('Test Company', currency_id=cls.currency_uah.id)['company']
        cls.env.company = cls.company
        cls.env.user.write({
            'company_id': cls.company.id,
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        cls.bank_journal = cls.env['account.journal'].search(
            [
                ('company_id', '=', cls.company.id),
                ('type', '=', 'bank')
            ],
            limit=1,
        )
        cls.bank_journal.currency_id = cls.currency_usd

        cls.env['res.currency.rate'].create([
            {
                'company_id': cls.company.id,
                'name': date(2023, 9, 1),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 39.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 9, 5),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 41.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 9, 15),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 42.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 4),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 36.5,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 5),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 39,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 11),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 40.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 13),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 40.5,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 15),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 37.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 10, 16),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 40.56,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 2),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 41.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 3),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 37.8396,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 4),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 38.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 5),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 39.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 9),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 41.5,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 10),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 36.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 11),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 37.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 19),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 39.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 11, 25),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 41.0,
            },
            {
                'company_id': cls.company.id,
                'name': date(2023, 12, 1),
                'currency_id': cls.currency_usd.id,
                'inverse_company_rate': 39.0,
            },
        ])

        cls.product = cls.env['product.product'].create({
            'name': 'товар 1',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'taxes_id': None,
        })

        cls.invoice_date = date(2023, 9, 6)      # SO/Invoice create date
