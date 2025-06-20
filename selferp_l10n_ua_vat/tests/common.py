from odoo import fields, Command
from odoo.tools.float_utils import float_round

from odoo.addons.selferp_contract_settlement.tests.common import AccountContractTestCommon


class VATTestCommon(AccountContractTestCommon):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):

        data = super().setup_company_data(company_name, chart_template, **kwargs)

        env = cls.env['account.move'].with_company(data['company']).env

        account_361 = env['account.account'].search([
            ('code', '=', '361000'),
            ('company_id', '=', env.company.id),
        ])
        assert account_361
        account_361.write({'first_event': True})

        account_631 = env['account.account'].search([
            ('code', '=', '631000'),
            ('company_id', '=', env.company.id),
        ])
        assert account_631

        account_631.write({'first_event': True})

        env.company.vat_journal_id = env['account.journal'].create({
            'company_id': env.company.id,
            'name': "VAT Journal",
            'code': 'VAT',
            'type': 'general',
        })
        env.company.vendor_vat_journal_id = env['account.journal'].create({
            'company_id': env.company.id,
            'name': "Vendor VAT Journal",
            'code': 'VVAT',
            'type': 'general',
        })

        first_event_journal = env['account.journal'].create({
            'name': "First Event Journal",
            'code': 'FEV',
            'type': 'general',
        })
        env.company.first_event_journal_id = first_event_journal

        (
            vat_account,
            vat_account_unconfirmed,
            vat_account_confirmed,
            vat_account_unconfirmed_credit,
            vat_account_confirmed_credit,
        ) = env.company.get_vat_default_accounts()

        # TODO: Some one add commented line but it not working. We should resolve meaning of it
        # vat_default_tax_credit = cls.env.company.get_vat_default_taxes()

        env.company.update({
            'vat_account_id': vat_account and vat_account.id or None,
            'vat_account_unconfirmed_id': vat_account_unconfirmed and vat_account_unconfirmed.id or None,
            'vat_account_confirmed_id': vat_account_confirmed and vat_account_confirmed.id or None,
            'vat_account_unconfirmed_credit_id': vat_account_unconfirmed_credit and vat_account_unconfirmed_credit.id or None,
            'vat_account_confirmed_credit_id': vat_account_confirmed_credit and vat_account_confirmed_credit.id or None,
            # 'vat_default_tax_credit_id': vat_default_tax_credit and vat_default_tax_credit.id or None,
        })

        default_tax = env['account.tax'].search(
            [
                ('company_id', '=', env.company.id),
                ('price_include', '=', True),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '20'),
            ],
            limit=1,
        )
        env.company.vat_default_tax_id = default_tax
        env.company.vat_default_tax_credit_id = default_tax

        default_vat_product = env['product.product'].create({'name': "vat_product"})
        env.company.vat_default_product_id = default_vat_product.id

        return data


    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        for tax in cls.env['account.tax'].search([]):
            if not tax.tax_group_id.is_vat:
                for line in tax.invoice_repartition_line_ids:
                    if line.account_id.code == '643100':
                        tax.tax_group_id.write({'is_vat': True})

        # TODO remove this hacks
        cls.account_361 = cls.env['account.account'].search([
            ('code', '=', '361000'),
            ('company_id', '=', cls.env.user.company_id.id),
        ])
        assert cls.account_361
        cls.account_361.write({'first_event': True})

        cls.account_631 = cls.env['account.account'].search([
            ('code', '=', '631000'),
            ('company_id', '=', cls.env.user.company_id.id),
        ])
        assert cls.account_631

        cls.account_631.write({'first_event': True})

        # TODO: Some one add commented line but it not working. We should resolve meaning of it
        # vat_default_tax_credit = cls.env.company.get_vat_default_taxes()

        cls.default_tax = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.env.company.id),
                ('price_include', '=', True),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '20'),
            ],
            limit=1,
        )
        cls.env.company.vat_default_tax_id = cls.default_tax
        cls.env.company.vat_default_tax_credit_id = cls.default_tax

        default_vat_product = cls.env['product.product'].create({'name': "vat_product"})
        cls.env.company.vat_default_product_id = default_vat_product.id

        cls.uom_unit_id = cls.env.ref('uom.product_uom_unit').id

        cls.amount_digits = cls.env['decimal.precision'].precision_get('Product Price')
        cls.quantity_digits = cls.env['decimal.precision'].precision_get('Product Unit of Measure')

        cls.tax_sale_20 = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.env.company.id),
                ('type_tax_use', '=', 'sale'),
                ('price_include', '=', True),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '20'),
            ],
            limit=1,
        )
        cls.tax_sale_20_exclude = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.env.company.id),
                ('type_tax_use', '=', 'sale'),
                ('price_include', '=', False),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '20'),
            ],
            limit=1,
        )
        cls.tax_sale_14 = cls.env['account.tax'].search(
            [
                ('company_id', '=', cls.env.company.id),
                ('type_tax_use', '=', 'sale'),
                ('price_include', '=', True),
                ('tax_group_id.is_vat', '=', True),
                ('tax_group_id.vat_code', '=', '14'),
            ],
            limit=1,
        )

        cls.tax_5_sale_incl = cls.env['account.tax'].create({
            'name': 'tax_5_sale_incl',
            'amount_type': 'percent',
            'amount': 5,
            'type_tax_use': 'sale',
            'price_include': True,
            'include_base_amount': True,
            #'is_base_affected': True,
            'sequence': 40,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'repartition_type': 'tax',
                }),
            ],
        })

        vat0_template = cls.env.ref('l10n_ua.sale_tax_template_vat0_psbo')
        cls.tax_sale_0 = cls.env['account.tax'].search(
            [
                ('name', '=', vat0_template.name),
                ('company_id', '=', cls.env.company.id),
                ('amount', '=', 0),
            ],
            limit=1,
        )

        vat_free_template = cls.env.ref('l10n_ua.sale_tax_template_vat_free_psbo')
        cls.tax_sale_free = cls.env['account.tax'].search(
            [
                ('name', '=', vat_free_template.name),
                ('company_id', '=', cls.env.company.id),
                ('amount', '=', 0),
            ],
            limit=1,
        )

    def calc_first_event_by_move(self, move):
        for record in move.line_ids:
            if record.account_id.first_event:
                return record._calc_first_event_by_move_line()

    def check_first_event(self, move, amount, error_message):
        if not amount:
            return
        for line in move.line_ids:
            if line.amount_first_event:
                self.assertEqual(amount, line.amount_first_event, error_message)
                return
        self.fail(error_message)

    def get_vat_invoice_1(self, move):
        for record in move.line_ids:
            if record.vat_invoice_id:
                return record.vat_invoice_id

    def dump_vat_move(self, move, message=""):
        ret = [message]
        if move:
            ret.append('move_type:' + move.move_type)
            ret.append('vat_lines ----')
            ret += [str(k) for k in move.vat_line_ids.read()]
            ret.append('lines ----')
            ret += [str(k) for k in move.line_ids.read()]
        return '\n'.join(ret)

    def check_vat_invoice(self, move, sum, message=False):
        vat_invoice_id = self.get_vat_invoice_1(move)
        if vat_invoice_id:
            self.assertEqual(sum, vat_invoice_id.vat_line_total, self.dump_vat_move(vat_invoice_id, message))
        else:
            self.assertEqual(sum, 0, self.dump_vat_move(vat_invoice_id, message))

    def check_move_line(self, move, account_code, product, field, amount, qty):
        for line in move.line_ids:
            if line.product_id and line.product_id.id == product.id:
                self.assertEqual(line.account_id.code, account_code, "Invalid account code %s" % account_code)
                self.assertEqual(
                    self.round_amount(line[field]),
                    self.round_amount(amount),
                    "Amount not equal for product %s" % product.name,
                )
                self.assertEqual(line.quantity, qty, "Qty not equal for product %s" % product.name)
                return
        self.fail("Line not found for product '%s', qty %.4f, amount %.2f" % (product.display_name, qty, self.round_amount(amount)))

    def check_move_line_account(self, move, account_code, field, amount):
        for line in move.line_ids:
            if (
                line.account_id
                and line.account_id.code == account_code
                and self.round_amount(line[field]) == self.round_amount(amount)
            ):
                return
        self.fail("Line not found for %s %.2f, account %s\nmove:\n%s" % (
            field,
            self.round_amount(amount),
            account_code,
            self.dump_vat_move(move),
        ))

    def check_vat_invoice_lines(self, vat_invoice, lines, message):
        for product, amount, qty, vat_amount in lines:
            amount_rounded = self.round_amount(amount)
            qty_rounded = self.round_qty(qty)
            vat_rounded = self.round_amount(vat_amount)
            for vat_line in vat_invoice.vat_line_ids:
                if (
                    vat_line.product_id == product
                    # TODO need to resolve rounding problem or move rounding out of loop (Many places in this file)
                    and self.round_amount(vat_line.total) == amount_rounded
                    and self.round_qty(vat_line.quantity) == qty_rounded
                    and self.round_amount(vat_line.vat_amount) == vat_rounded
                ):
                    return
            self.fail('%s: cannot find line for %s, amount: %s, qty: %s, vat: %s \n invoice: \n %s' %(
                message,
                product.display_name,
                amount,
                qty,
                vat_amount,
                self.dump_vat_move(vat_invoice),
            ))

    def check_first_events_data(self, data, move, sum, message=False):
        fe_sum = 0
        for data_line in data:
            for move_line in move.line_ids:
                if data_line['id'] == move_line.id:
                    first_event = move_line['amount_first_event']
                    fe_sum += first_event
        self.assertEqual(sum, fe_sum, message)

    @classmethod
    def create_sale_order_invoice(cls, so, partner, products, amounts, taxes=None, date=None, company=False):
        move = cls.create_invoice(partner, products, amounts, taxes, date, company)
        for move_line in move.line_ids:
            for soline in so.order_line:
                if move_line.product_id and move_line.product_id.id == soline.product_id.id:
                    move_line.update({
                        'sale_line_ids': [fields.Command.set([soline.id])],
                    })
        return move

    @classmethod
    def generate_vat_documents(cls, company_id, date_begin, date_end):
        cls.env['account.vat.calculations'].generate_vat_documents(company_id, date_begin, date_end)

    @classmethod
    def round_amount(cls, amount):
        return float_round(amount, cls.amount_digits)

    @classmethod
    def round_qty(cls, qty):
        return float_round(qty, cls.quantity_digits)

    @classmethod
    def vat_of(cls, amount, tax=None):
        # This assumes tax type is percent, default vat 20%
        return cls.round_amount(tax._compute_amount(amount, 0) if tax else amount * (1 - 1 / 1.2))

    @classmethod
    def without_vat(cls, amount, tax=None):
        # This assumes tax type is percent, default vat 20%
        return cls.round_amount(amount - tax._compute_amount(amount, tax) if tax else amount / 1.2)

    @classmethod
    def calc_vat_line_params(cls, price, qty, factor=1, tax=None, dsc=1):
        """
        Returns tuple (amount, qty, tax_amount) according to factor
        """
        amount = price * qty * dsc
        return amount * factor, qty * factor, cls.vat_of(amount * factor, tax)

    @classmethod
    def generate_vat_documents_by_partner(cls, partner, date_begin, date_end):
        return cls.env['account.vat.calculations'].generate_vat_documents_by_partners([partner.id], date_begin, date_end)


class VATTestCommonPriceVATIncl(VATTestCommon):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        result = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        if result:
            company = result.get('company')
            if company:
                account_sale_tax_id = cls.env['account.tax'].search(
                    [
                        ('type_tax_use', '=', 'sale'),
                        ('company_id', '=', company.id),
                        ('price_include', '=', True),
                    ],
                    limit=1,
                )
                account_purchase_tax_id = cls.env['account.tax'].search(
                    [
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id', '=', company.id),
                        ('price_include', '=', True),
                    ],
                    limit=1,
                )
                company.write({
                    'account_sale_tax_id': account_sale_tax_id.id,
                    'account_purchase_tax_id': account_purchase_tax_id.id,
                })
                result.update({
                    'default_tax_sale': account_sale_tax_id,
                    'default_tax_purchase': account_purchase_tax_id,
                })
        return result
