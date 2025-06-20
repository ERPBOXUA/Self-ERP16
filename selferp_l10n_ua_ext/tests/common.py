from odoo import Command, fields
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class AccountTestCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = 'l10n_ua.l10n_ua_psbo_chart_template'

        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.bank_journal = cls.company_data['default_journal_bank']
        assert cls.bank_journal, "No appropriate bank journal found"

    @classmethod
    def create_sale_order(cls, partner, products, counts, prices, contract=None, date_order=None, discounts=None, currency=None):
        assert len(products) == len(counts), "Products and counts should have same count of elements"
        assert len(products) == len(prices), "Products and prices should have same count of elements"

        lines = [
            Command.create({
                'product_id': product.id,
                'product_uom_qty': counts[i],
                'price_unit': prices[i],
                'discount': discounts[i] if discounts else 0,
            })
            for i, product in enumerate(products)
        ]

        sale_values = {
            'partner_id': partner.id,
            'order_line': lines,
        }

        SaleOrder = cls.env['sale.order']
        if 'contract_id' in SaleOrder._fields:
            sale_values['contract_id'] = contract and contract.id or None

        if currency:
            sale_values['currency_id'] = currency.id

        sale_order = SaleOrder.create(sale_values)
        if date_order:
            cls.env.cr.execute('''
                UPDATE sale_order 
                   SET create_date = %s, 
                       date_order = %s    
            ''', (date_order, date_order))

        return sale_order

    @classmethod
    def confirm_sale_order(cls, sale_order, date_order=None):
        sale_order.action_confirm()
        if date_order:
            cls.env.cr.execute('''
                UPDATE sale_order
                   SET date_order = %s
            ''', (date_order,))
        assert sale_order.state == 'sale', "Sale order confirmation failed"

    @classmethod
    def deliver_sale_order(cls, sale_order):
        for line in sale_order.order_line:
            line.qty_delivered = line.product_uom_qty

    @classmethod
    def invoicing_sale_order(cls, sale_order, date=None):
        moves = sale_order._create_invoices(date=date)
        assert len(moves) == 1, "Invoiced more than one invoice"
        invoice = moves[0]
        return invoice

    @classmethod
    def create_invoice(cls, partner, products, amounts, taxes=None, date=None, company=None, sale_order=None, currency=None):
        date = date or fields.Date.today()
        move = cls.init_invoice(
            'out_invoice',
            partner=partner,
            invoice_date=date,
            post=False,
            products=products,
            amounts=amounts,
            taxes=taxes,
            company=company,
        )
        if sale_order:
            move.write({
                'ref': sale_order.client_order_ref or '',
                'narration': sale_order.note,
                'invoice_origin': sale_order.name,
                'payment_reference': sale_order.reference,
            })
            for product in products:
                so_line = sale_order.order_line.filtered(lambda rec: rec.product_id == product)
                inv_line = move.line_ids.filtered(lambda rec: rec.product_id == product)
                if so_line and inv_line:
                    inv_line.sale_line_ids = [Command.link(so_line.id)]

        cls.env.cr.execute('''
            UPDATE account_move
               SET create_date = %s    
             WHERE id = %s    
        ''', (fields.Datetime.to_string(date), move.id))

        if currency:
            move.write({'currency_id': currency.id})

        return move

    # Full rewrite method: in case uses both products and amounts to test product part of invoice
    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=None, amounts=None, taxes=None, company=False, currency=None):
        if not products or not amounts:
            return super().init_invoice(
                move_type,
                partner=partner,
                invoice_date=invoice_date,
                post=post,
                products=products,
                amounts=amounts,
                taxes=taxes,
                company=company,
                currency=currency,
            )

        products = [] if products is None else products
        amounts = [] if amounts is None else amounts
        move_form = Form(
            cls.env['account.move']
               .with_company(company or cls.env.company)
               .with_context(default_move_type=move_type, account_predictive_bills_disable_prediction=True)
        )
        move_form.invoice_date = invoice_date or fields.Date.from_string('2019-01-01')

        if not move_form._get_modifier('date', 'invisible'):
            move_form.date = move_form.invoice_date
        move_form.partner_id = partner or cls.partner_a
        if currency:
            move_form.currency_id = currency

        for i, product in enumerate(products):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                line_form.price_unit = amounts[i]
                if taxes is not None:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        ret = move_form.save()

        if post:
            ret.action_post()

        return ret

    @classmethod
    def post_invoice(cls, invoice, invoice_date=None):
        if not invoice.invoice_date:
            invoice.invoice_date = invoice_date or fields.Date.today()
            invoice.date = invoice_date or fields.Date.today()

        invoice.action_post()

        assert invoice.state == 'posted', "Invoice posting failed"

    def pay_invoice(self, invoice):
        reg = self.env['account.payment.register'].with_context({
            'active_model': 'account.move',
            'active_ids': invoice.ids,
        }).create({})

        payments = reg._create_payments()

        self.assertGreater(len(payments), 0, "Payments not created")

        return payments

    def refund_invoice(self, invoice):
        reverse = self.env['account.move.reversal'].with_context({
            'active_model': 'account.move',
            'active_ids': invoice.ids,
        }).create({
            'journal_id': invoice.journal_id.id,
            'refund_method': 'refund',
        })

        reverse.reverse_moves()

        refund = reverse.new_move_ids

        self.assertGreater(len(refund), 0, "Refund not created")

        return refund

    def refund_payment(self, payment, date=None):
        raise NotImplementedError()

    def refund_invoice_partly(self, invoice, products, qtys, date_refund):
        refund = self.refund_invoice(invoice)

        refund.invoice_date = date_refund

        for line in refund.line_ids:
            for i, product in enumerate(products):
                if product == line.product_id:
                    line.quantity = qtys[i]

        return refund

    def create_bank_statement_line(self, partner, amount, ref='payment', date=None):
        date = date or fields.Date.today()
        values = {
            'date': date,
            'payment_ref': ref,
            'partner_id': partner.id,
            'amount': amount,
            'journal_id': self.bank_journal.id,
        }
        statement_line = self.env['account.bank.statement.line'].create(values)

        self.env.cr.execute('''
            UPDATE account_bank_statement_line
               SET create_date = %s    
             WHERE id = %s    
        ''', (fields.Datetime.to_string(date), statement_line.id))

        return statement_line

    def validate_statement_line(self, statement_line, invoice=None, invoice_lines=None, remove_new_amls=False):
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement_line.id).new({})

        wizard._action_trigger_matching_rules()

        if invoice:
            wizard._action_add_new_amls(invoice.line_ids[1])
        if invoice_lines:
            wizard._action_add_new_amls(invoice_lines)
        if remove_new_amls:
            new_aml = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
            while new_aml:
                wizard._action_remove_line(new_aml[0].index)
                new_aml = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')

        self.assertEqual(wizard.state, 'valid', "Account bank statement line is invalid")

        wizard.button_validate(async_action=False)

        self.assertTrue(statement_line.move_id, "It should create move")

        return statement_line.move_id

    @classmethod
    def create_purchase_order(cls, partner, products, counts, prices, contract=None, date=None, currency=None):
        assert len(products) == len(counts), "Products and counts should have same count of elements"
        assert len(products) == len(prices), "Products and prices should have same count of elements"

        lines = [
            Command.create({
                'product_id': product.id,
                'product_qty': counts[i],
                'price_unit': prices[i],
            })
            for i, product in enumerate(products)
        ]

        values = {
            'partner_id': partner.id,
            'date_order': date or fields.Date.today(),
            'order_line': lines,
        }
        if contract:
            values['contract_id'] = contract.id
        if currency:
            values['currency_id'] = currency.id

        purchase_order = cls.env['purchase.order'].create(values)
        assert len(purchase_order.order_line) == len(products)
        return purchase_order

    @classmethod
    def confirm_purchase_order(cls, purchase_order):
        assert purchase_order.button_confirm()

        return purchase_order

    @classmethod
    def receive_purchase_order(cls, purchase_order, qtys=None):
        line_num = 0
        for line in purchase_order.order_line:
            if not qtys:
                line.qty_received = line.product_qty
            else:
                line.qty_received = qtys[line_num]
                line_num += 1

    @classmethod
    def receive_purchase_order_full(cls, purchase_order):
        transfer_action = purchase_order.picking_ids.button_validate()
        cls.env[transfer_action.get('res_model')].with_context(transfer_action.get('context')).create({}).process()

    @classmethod
    def confirm_and_receive_purchase_order(cls, purchase_order):
        purchase_order.button_confirm()

        transfer_action = purchase_order.picking_ids.button_validate()
        cls.env[transfer_action.get('res_model')].with_context(transfer_action.get('context')).create({}).process()

    @classmethod
    def invoicing_purchase_order(cls, purchase_order):
        action = purchase_order.action_create_invoice()
        assert 'res_id' in action
        invoice_id = action['res_id']
        invoice = cls.env['account.move'].browse(invoice_id)
        assert invoice
        return invoice

    def create_contract_bank_statement_line(self, partner, amount, contract=None, ref='payment', date=None, sale_order=None, purchase_order=None, currency=None, amount_currency=None, counterpart_account_id=None):
        AccountBankStatementLine = self.env['account.bank.statement.line']

        values = {
            'date': date or fields.Date.today(),
            'payment_ref': ref,
            'partner_id': partner.id,
            'amount': amount,
            'journal_id': self.bank_journal.id,
            'counterpart_account_id': counterpart_account_id,
        }

        if contract and 'contract_id' in AccountBankStatementLine._fields:
            values['contract_id'] = contract.id

        if sale_order and 'linked_sale_order_id' in AccountBankStatementLine._fields:
            values['linked_sale_order_id'] = sale_order.id

        if purchase_order and 'linked_purchase_order_id' in AccountBankStatementLine._fields:
            values['linked_purchase_order_id'] = purchase_order.id

        if currency:
            values['foreign_currency_id'] = currency.id

        if amount_currency:
            values['amount_currency'] = amount_currency

        statement_line = AccountBankStatementLine.create(values)

        return statement_line

    @classmethod
    def create_contract(cls, name, partner, operation_type='sale', contract_date=None):
        contract = cls.env['account.contract'].create({
            'name': name,
            'partner_id': partner.id,
            'operation_type': operation_type,
            'date_start': contract_date,
        })
        return contract
