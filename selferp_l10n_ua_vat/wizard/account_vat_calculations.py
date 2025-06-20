from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv.expression import AND
from odoo.tools import float_round


class AccountVatCalculations(models.TransientModel):
    _name = 'account.vat.calculations'
    _description = "VAT Calculations"

    period_begin_date = fields.Date(
        string="Date begin",
        required=True,
    )

    period_end_date = fields.Date(
        string="Date end",
        required=True,
    )

    def action_vat_proceed(self):
        self.ensure_one()
        vat_documents = self.generate_vat_documents(self.env.company.id, self.period_begin_date, self.period_end_date)
        if not vat_documents:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'sticky': False,
                    'title': _("Warning!"),
                    'message': _("No any VAT invoice created"),
                },

            }
        else:
            action = self.env.ref('selferp_l10n_ua_vat.account_move_action_vat_invoice').read()[0]

            if len(vat_documents) > 1:
                action['domain'] = [('id', 'in', vat_documents.ids)]
                return {
                    'type': 'ir.actions.act_multi',
                    'actions': [
                        {'type': 'ir.actions.act_view_reload'},
                        action,
                    ],
                }
            else:
                action.update({
                    'res_id': vat_documents.id,
                    'view_mode': 'form',
                })
                return {
                    'type': 'ir.actions.act_multi',
                    'actions': [
                        {'type': 'ir.actions.act_view_reload'},
                        action,
                    ],
                }

    @api.model
    def correct_vat_rest(self, so_info, vat_invoice):
        for line in vat_invoice.line_ids:
            if line.product_id:
                for so_line in so_info['products']:
                    if so_line['id'] == line.product_id.id:
                        so_line['vat_payed'] += line.credit
                        so_line['vat_qty'] += line.quantity

    @api.model
    def get_so_line_vat(self, so_line):
        return so_line.get_ua_vat()

    @api.model
    def get_so_line_before_vat(self, so_line):
        return so_line.get_taxes_before_ua_vat()

    @api.model
    def get_po_line_vat(self, po_line):
        return po_line.get_ua_vat()

    @api.model
    def find_so_info(self, so_id):
        products = []
        result = {'products': products}
        so = self.env['sale.order'].browse(so_id)
        for line in so.order_line:
            vat = self.get_so_line_vat(line)
            taxes = self.get_so_line_before_vat(line)
            tax = line.get_ua_vat_tax()
            if tax:
                products.append({
                    'id': line.product_id.id,
                    'name': line.name,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_total': line.price_total,
                    'price_subtotal': line.price_subtotal,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'tax_id': tax.id,
                    'before_vat_ids': taxes.ids,
                    'vat': vat,
                    'vat_payed': 0,
                    'vat_qty': 0,
                })
        return result

    @api.model
    def find_po_info(self, so_id):
        vat_lines = {}
        result = {'vats': vat_lines}
        order = self.env['purchase.order'].browse(so_id)
        order_lines = order.order_line.filtered(lambda x: not x.display_type)
        for line in order_lines:
            vat = self.get_po_line_vat(line)
            tax = line.get_ua_vat_tax()
            if tax:
                if tax.id not in vat_lines:
                    vat_lines[tax.id] = {'vat': 0.0, 'sum': 0.0}
                vat_lines[tax.id]['vat'] += vat
                vat_lines[tax.id]['sum'] += line.price_total
        return result

    @api.model
    def create_po_first_event_move(self, move_line, first_event, po_info, contract=None, po_id=None):
        AccountTax = self.env['account.tax']
        acc_vat_confirmed = move_line.move_id.company_id.vat_account_confirmed_credit_id
        acc_vat_unconfirmed = move_line.move_id.company_id.vat_account_unconfirmed_credit_id
        first_event_journal = move_line.move_id.company_id.first_event_journal_id
        first_event_lines = []

        def add_vat_first_event_lines(tax, tax_amount):
            first_event_lines.append(fields.Command.create({
                'account_id': acc_vat_confirmed.id,
                'credit': tax_amount,
                'name': tax.name,
                'vat_invoice_tax_id': tax.id,
                'partner_id': partner_id,
            }))
            first_event_lines.append(fields.Command.create({
                'account_id': acc_vat_unconfirmed.id,
                'debit': tax_amount,
                'name': tax.name,
                'vat_invoice_tax_id': tax.id,
                'linked_purchase_order_id': po_id,
                'contract_id': contract,
                'partner_id': partner_id,
            }))

        partner_id = move_line.move_id.partner_id.id
        if po_info:
            sum_vats = po_info['vats']
            sum_amount = sum(value['sum'] for value in sum_vats.values())
            coefficient = first_event / sum_amount if sum_amount else 1

            for (tax_id, tax_data) in sum_vats.items():
                tax = AccountTax.browse(tax_id)

                tax_amount = coefficient * tax_data['vat']

                add_vat_first_event_lines(tax, tax_amount)
        else:
            tax = self.env.company.vat_default_tax_credit_id
            tax_amount = tax._compute_amount(first_event, first_event)

            add_vat_first_event_lines(tax, tax_amount)

        fe_move = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': first_event_lines,
            'contract_id': contract,
            'journal_id': first_event_journal.id,
            'partner_id': partner_id,
            'ref': move_line.move_id.name,
            'first_event_source_id': move_line.move_id.id,
            'date': move_line.move_id.date,
        })

        move_line.update({'vat_first_event_move_id': fe_move.id})

        fe_move._post()

        return fe_move

    @api.model
    def create_vat_invoice(self, move, first_event, so_info, contract=None, so_id=None, partner=None, ref=None):
        def _create_line_by_prod_info(coefficient, prod, sum_vats, currency):
            qty_digits = self.env['decimal.precision'].precision_get('VAT quantity')
            qty = float_round(coefficient * prod['product_uom_qty'], precision_digits=qty_digits)
            dsc = (100 - (prod['discount'] if 'discount' in prod else 0))/100
            total = currency.round(qty * prod['price_unit'] * dsc)
            taxes = AccountTax.browse(0)
            taxes += AccountTax.browse(prod['before_vat_ids'])
            tax = AccountTax.browse(prod['tax_id'])
            taxes += tax
            tax_calc = taxes.compute_all(price_unit=prod['price_unit'] * dsc, quantity=qty)
            vat_calc = next(x for x in tax_calc['taxes'] if x['id'] == prod['tax_id'])
            tax_amount = vat_calc['amount']
            if sum_vats.get(tax.id):
                sum_vats[tax.id] += tax_amount
            else:
                sum_vats[tax.id] = tax_amount
            ret_line = {
                'product_id': prod['id'],
                'product_uom_id': prod['product_uom'],
                'quantity': qty,
                'price_unit': prod['price_unit'],
                'discount': prod['discount'],
                'tax_before_vat_ids': prod['before_vat_ids'],
                'vat_tax_id': tax.id,
                'total_manual': total,
                'total': total,
            }
            if total < 0:
                ret_line['adjustment_cause_type'] = 'quantity'
                ret_line['adjustment_reason_type'] = '103'
            return ret_line

        AccountTax = self.env['account.tax']
        acc_vat_confirmed = self.env.company.vat_account_confirmed_id
        acc_vat_unconfirmed = self.env.company.vat_account_unconfirmed_id
        acc_vat = self.env.company.vat_account_id
        journal_id = self.env.company.vat_journal_id
        first_event_journal_id = self.env.company.first_event_journal_id
        product_lines = []
        first_event_lines = []
        sum_total = 0
        sum_vat_payed = 0
        sum_amount = 0
        sum_vats = {}
        to_check = False

        is_storno = first_event < 0

        partner_id = move.partner_id.id if move else partner.id

        if move:
            currency_id = move.move_id.currency_id
        else:
            currency_id = self.env.company.currency_id

        if is_storno:
            if move.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                products = move.move_id.invoice_line_ids
                for prod in products:
                    sum_total += prod.price_total
                    sum_amount += prod.price_total
                    sum_vat_payed += prod.amount_vat_tax
                if sum_total:
                    coefficient = first_event / sum_total
                    for prod in products:
                        total = coefficient * prod.price_total
                        tax = prod.vat_tax_id
                        tax_amount = tax._compute_amount(coefficient * prod.quantity * prod.price_unit, prod.price_unit, move.move_id.currency_id)
                        if sum_vats.get(tax.id):
                            sum_vats[tax.id] += tax_amount
                        else:
                            sum_vats[tax.id] = tax_amount
                        product_lines.append(fields.Command.create({
                            'product_id': prod.product_id.id,
                            'product_uom_id': prod.product_uom_id.id,
                            'quantity': coefficient * prod.quantity,
                            'price_unit': prod.price_unit,
                            'vat_tax_id': tax.id,
                            'total_manual': total,
                            'total': total,
                            'discount': prod.discount,
                            'adjustment_cause_type': 'quantity',
                            'adjustment_reason_type': '103',
                        }))
            elif so_info:
                products = so_info['products']
                for prod in products:
                    sum_total += prod['price_total']
                    sum_amount += prod['price_total']
                    sum_vat_payed += prod['vat_payed']
                if sum_total:
                    coefficient = first_event / sum_total
                    doc_total = 0
                    for prod in products:
                        if prod == products[-1]:
                            # last line cents rounding
                            for (tax_id, tax_amount) in sum_vats.items():
                                tax = AccountTax.browse(tax_id)
                                if not tax.price_include:
                                    doc_total += tax_amount
                            coefficient = first_event / (doc_total + prod['price_total'])
                        line = _create_line_by_prod_info(coefficient, prod, sum_vats, currency_id)
                        doc_total += line['total']
                        product_lines.append(fields.Command.create(line))

        else:
            if so_info:
                products = so_info['products']
                for prod in products:
                    sum_total += prod['price_total']
                    sum_amount += prod['price_total']
                    sum_vat_payed += prod['vat_payed']
                if sum_total:
                    coefficient = first_event / sum_total
                    doc_total = 0
                    for prod in products:
                        if prod == products[-1]:
                            # last line cents rounding
                            for (tax_id, tax_amount) in sum_vats.items():
                                tax = AccountTax.browse(tax_id)
                                if not tax.price_include:
                                    doc_total += tax_amount
                            coefficient = (first_event - doc_total) / prod['price_total']
                        line = _create_line_by_prod_info(coefficient, prod, sum_vats, currency_id)
                        doc_total += line['total']
                        product_lines.append(fields.Command.create(line))

            else:
                default_product = self.env.company.vat_default_product_id
                to_check = True
                total = first_event
                tax = self.env.company.vat_default_tax_id
                tax_amount = tax._compute_amount(total, total)
                sum_vats[tax.id] = tax_amount
                product_lines.append(fields.Command.create({
                    'product_id': default_product.id,
                    'product_uom_id': default_product.uom_id.id,
                    'quantity': 1,
                    'price_unit': total,
                    'vat_tax_id': tax.id,
                    'total_manual': total,
                }))

        sum_tax = 0
        for (tax_id, tax_amount) in sum_vats.items():
            sum_tax += tax_amount
            tax = AccountTax.browse(tax_id)

            line1 = {
                'account_id': acc_vat_confirmed.id,
                'name': tax.name,
                'partner_id': partner_id,
            }
            if is_storno:
                line1['credit'] = -tax_amount
            else:
                line1['debit'] = tax_amount

            first_event_lines.append(fields.Command.create(line1))

            line2 = {
                'account_id': acc_vat_unconfirmed.id,
                'name': tax.name,
                'vat_invoice_tax_id': tax.id,
                'linked_sale_order_id': so_id,
                'contract_id': contract,
                'partner_id': partner_id,
            }
            if is_storno:
                line2['debit'] = -tax_amount
            else:
                line2['credit'] = tax_amount

            first_event_lines.append(fields.Command.create(line2))

        #TODO need data and ref value from POS

        invoice = self.env['account.move'].create({
            'move_type': 'vat_invoice' if first_event > 0 else 'vat_adjustment_invoice',
            'vat_line_ids': product_lines,
            'partner_id': partner_id,
            'contract_id': contract,
            'journal_id': journal_id.id,
            'ref': ref or (move and move.name) or None,
            'date': move.date if move else datetime.now(),
            'to_check': to_check,
            'vat_sale_order_id': so_id,
            'is_storno': is_storno,
        })

        if move:
            fe_move = self.env['account.move'].create({
                'move_type': 'entry',
                'line_ids': first_event_lines,
                'contract_id': contract,
                'journal_id': first_event_journal_id.id,
                'partner_id': partner_id,
                'ref': move.name,
                'date': move.date,
                'is_storno': is_storno,
                'first_event_vat_invoice_id': invoice.id,
                'vat_sale_order_id': so_id,
            })

            move.update({
                'vat_invoice_id': invoice.id,
                'vat_first_event_move_id': fe_move.id,
            })

            fe_move._post()

        return invoice

    @api.model
    def get_so_id_from_move_line(self, move_line):
        so_id = None
        if move_line.linked_sale_order_id:
            return move_line.linked_sale_order_id.id
        if move_line.move_id.move_type == 'out_invoice' and move_line.move_id.sale_order_count == 1:
            so_id = move_line.move_id.line_ids.sale_line_ids.order_id.id
        if not so_id:
            for line in move_line.move_id.line_ids:
                if line.linked_sale_order_id:
                    return line.linked_sale_order_id.id
        return so_id

    @api.model
    def get_po_id_from_move_line(self, move_line):
        po_id = None
        if move_line.linked_purchase_order_id:
            return move_line.linked_purchase_order_id.id
        if move_line.move_id.move_type == 'in_invoice' and move_line.move_id.purchase_order_count == 1:
            po_id = move_line.move_id.line_ids.purchase_line_id.order_id.id
        if not po_id:
            for line in move_line.move_id.line_ids:
                if line.linked_purchase_order_id:
                    return line.linked_purchase_order_id.id
        return po_id

    def get_move_line_ids_empty_so_id(self, partner_id, company_id):
        lines = self.env['account.move.line'].search([
            ('linked_sale_order_id', '=', None),
            ('partner_id', '=', partner_id),
            ('company_id', '=', company_id),
        ])
        return lines.ids

    def get_move_line_ids_by_so_id(self, so_id):
        if not so_id:
            raise UserError('No sale order found in method get_move_line_ids_by_so_id')

        move_ids = []
        sale_order = self.env['sale.order'].browse(so_id)

        move_ids += sale_order.order_line.invoice_lines.ids

        lines = self.env['account.move.line'].search([('linked_sale_order_id', '=', so_id)])

        move_ids += lines.ids

        return move_ids

    def get_move_line_ids_empty_po_id(self, partner_id, company_id):
        lines = self.env['account.move.line'].search([
            ('linked_purchase_order_id', '=', False),
            ('partner_id', '=', partner_id),
            ('company_id', '=', company_id),
        ])
        return lines.ids

    def get_move_line_ids_by_po_id(self, po_id):
        if not po_id:
            raise UserError('No purchase order found in method get_move_line_ids_by_po_id')

        move_ids = []
        purchase_order = self.env['purchase.order'].browse(po_id)

        move_ids += purchase_order.order_line.invoice_lines.ids

        lines = self.env['account.move.line'].search([('linked_purchase_order_id', '=', po_id)])

        move_ids += lines.ids

        return move_ids

    def get_contract_id_from_move_line(self, move_line):
        if move_line.contract_id:
            return move_line.contract_id.id
        if move_line.move_id.contract_id:
            return move_line.move_id.contract_id
        return None

    def get_move_line_ids_without_contract_id(self, partner_id, company_id):
        if not partner_id or not company_id:
            raise UserError('No partner or company found in method get_move_line_ids_without_contract_id')
        return self.env['account.move.line'].search([
            ('contract_id', '=', None),
            ('partner_id', '=', partner_id),
            ('company_id', '=', company_id),
        ]).ids

    def get_move_line_ids_by_contract_id(self, contract_id):
        return self.env['account.move.line'].search([('contract_id', '=', contract_id)]).ids

    @api.model
    def generate_vat_documents(self, company_id, date_begin, date_end):
        self.env.flush_all()
        self.env.cr.execute("""
            SELECT DISTINCT 
                   move.partner_id as partner_id
              FROM account_move_line line,
                   account_move move,
                   account_account acount
             WHERE line.move_id = move.id
               AND acount.id = line.account_id
               AND acount.first_event = True
               AND line.company_id = %(company_id)s
               AND line.date >= %(date_begin)s
               AND line.date <= %(date_end)s
        """, {
             'company_id': company_id,
             'date_begin': date_begin,
             'date_end': date_end,
        })

        partner_ids = self.env.cr.fetchall()
        partner_ids = [r[0] for r in partner_ids]

        vat_documents = self.generate_vat_documents_by_partners(partner_ids, date_begin, date_end, company_ids=[company_id])
        return vat_documents

    def generate_vat_documents_by_partners(self, partner_ids, date_begin, date_end, vendor=None, company_ids=None):
        documents = self.env['account.move'].browse()

        partners = self.env['res.partner'].browse(partner_ids)

        if company_ids:
            companies = company_ids
        else:
            companies = self.env.companies.ids

        for company_id in companies:
            for partner in partners:
                tracking = partner.tracking_first_event_vendor if vendor else partner.tracking_first_event
                if tracking == 'in_general':
                    first_events = self._calc_first_event([
                        ('move_id.partner_id', '=', partner.id),
                        ('move_id.company_id', '=', company_id),
                    ], vendor=vendor)
                    first_events = self._filter_first_events(first_events, date_begin, date_end)
                    documents += self._create_vat_moves(first_events, vendor=vendor)

                elif tracking == 'by_contract':
                    self.env.flush_all()
                    self.env.cr.execute('''
                        SELECT DISTINCT line.contract_id as contract_id
                          FROM account_move_line line,
                               account_move move,
                               account_account acount
                         WHERE line.move_id = move.id
                           AND acount.id = line.account_id
                           AND acount.first_event = True
                           AND move.company_id = %(company_id)s
                           AND move.partner_id = %(partner_id)s
                           AND move.date >= %(date_begin)s
                           AND move.date <= %(date_end)s
                    ''', {
                        'company_id': company_id,
                        'partner_id': partner.id,
                        'date_begin': date_begin,
                        'date_end': date_end,
                    })

                    data = self.env.cr.fetchall()

                    contracts_data = [el[0] for el in data]

                    for contract_id in contracts_data:
                        if not contract_id:
                            move_lines = self.get_move_line_ids_without_contract_id(partner.id, company_id)
                        else:
                            move_lines = self.get_move_line_ids_by_contract_id(contract_id)
                        first_events = self.env['account.vat.calculations']._calc_first_event(
                            [
                                ('id', 'in', move_lines),
                            ],
                            vendor=vendor,
                        )
                        first_events = self._filter_first_events(first_events, date_begin, date_end)
                        documents += self._create_vat_moves(first_events, contract=contract_id, vendor=vendor)

                elif tracking == 'by_order':
                    self.env.flush_all()
                    if vendor:
                        field_name = 'linked_purchase_order_id'
                    else:
                        field_name = 'linked_sale_order_id'
                    self.env.cr.execute('''
                        SELECT DISTINCT line.%s as order_id
                          FROM account_move_line line,
                               account_move move,
                               account_account acount
                         WHERE line.move_id = move.id
                           AND acount.id = line.account_id
                           AND acount.first_event = True
                           AND move.company_id = %%(company_id)s
                           AND move.partner_id = %%(partner_id)s
                           AND move.date >= %%(date_begin)s
                           AND move.date <= %%(date_end)s
                    ''' % field_name, {
                        'company_id': company_id,
                        'partner_id': partner.id,
                        'date_begin': date_begin,
                        'date_end': date_end,
                    })

                    data = self.env.cr.fetchall()

                    order_data = [so[0] for so in data]
                    for order_id in order_data:
                        if order_id:
                            if vendor:
                                move_lines = self.get_move_line_ids_by_po_id(order_id)
                            else:
                                move_lines = self.get_move_line_ids_by_so_id(order_id)
                        else:
                            if vendor:
                                move_lines = self.get_move_line_ids_empty_po_id(partner.id, company_id)
                            else:
                                move_lines = self.get_move_line_ids_empty_so_id(partner.id, company_id)

                        first_events = self._calc_first_event(
                            [
                                ('id', 'in', move_lines),
                            ],
                            vendor=vendor,
                        )
                        first_events = self._filter_first_events(first_events, date_begin, date_end)
                        if vendor:
                            documents += self._create_vat_moves(first_events, po_id=order_id, vendor=vendor)
                        else:
                            documents += self._create_vat_moves(first_events, so_id=order_id, vendor=vendor)
                else:
                    raise ValueError(_("Not known VAT tracking variant: %s", tracking))

        return documents

    def _create_vat_moves(self, first_events, contract=None, so_id=None, po_id=None, vendor=False):
        created = self.env['account.move'].browse()

        if vendor:
            po_infos = {}
            for first_event in first_events:
                event_amount = first_event['amount_first_event']
                if event_amount != 0:
                    move_line = self.env['account.move.line'].browse(first_event['id'])

                    po_id = self.get_po_id_from_move_line(move_line)

                    po_info = None
                    if po_id:
                        po_info = po_infos.get(po_id)
                        if not po_info:
                            po_info = self.find_po_info(po_id)
                            if po_info:
                                po_infos[po_id] = po_info

                    if po_info:
                        if not move_line.vat_first_event_move_id:
                            created += self.create_po_first_event_move(move_line, event_amount, po_info, contract=contract)
                        
                    else:
                        created += self.create_po_first_event_move(move_line, event_amount, None)

        else:

            so_infos = {}
            for first_event in first_events:
                event_amount = first_event['amount_first_event']
                if event_amount != 0:
                    move_line = self.env['account.move.line'].browse(first_event['id'])

                    so_id = self.get_so_id_from_move_line(move_line)

                    so_info = None
                    if so_id:
                        so_info = so_infos.get(so_id)
                        if not so_info:
                            so_info = self.find_so_info(so_id)
                            if so_info:
                                so_infos[so_id] = so_info

                    if so_info:
                        if move_line.vat_invoice_id:
                            vat_invoice = move_line.vat_invoice_id
                            self.correct_vat_rest(so_info, vat_invoice)
                        else:
                            if event_amount != 0:
                                vat_invoice = self.create_vat_invoice(move_line, event_amount, so_info, contract=contract, so_id=so_id)
                                created += vat_invoice
                                self.correct_vat_rest(so_info, vat_invoice)
                    else:
                        created += self.create_vat_invoice(move_line, event_amount, None, contract=contract, so_id=so_id)

        return created

    @api.model
    def _filter_first_events(self, first_events, date_begin, date_end):
        dat_begin = date_begin.date() if isinstance(date_begin, datetime) else date_begin
        dat_begin = datetime.strptime(dat_begin, '%Y-%m-%d').date() if isinstance(dat_begin, str) else dat_begin

        dat_end = date_end.date() if isinstance(date_end, datetime) else date_end
        dat_end = datetime.strptime(dat_end, '%Y-%m-%d').date() if isinstance(dat_end, str) else dat_end

        ret = [fe for fe in first_events if dat_begin <= fe['date'] <= dat_end]
        return ret

    @api.model
    def _calc_first_event(self, move_domain, start_sum=0, vendor=False):
        def _make_bank_storno(bank_data_lines, vendor):
            for bank_line in data_lines:
                move_id = self.env['account.move'].browse(bank_line['move_id'][0])
                if not vendor:
                    if move_id.statement_line_id and not bank_line['is_storno'] and bank_line['balance'] > 0:
                        bank_line['is_storno'] = True
                        bank_line['credit'] = - bank_line['debit']
                        bank_line['debit'] = 0
                else:
                    if move_id.statement_line_id and not bank_line['is_storno'] and bank_line['balance'] < 0:
                        bank_line['is_storno'] = True
                        bank_line['debit'] = - bank_line['credit']
                        bank_line['credit'] = 0

        ret = []
        if vendor:
            additional_domain = [
                ('account_id.first_event', '=', True),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'liability_payable'),
            ]
        else:
            additional_domain = [
                ('account_id.first_event', '=', True),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'asset_receivable'),
            ]

        data_lines = self.env['account.move.line'].search_read(
            domain=AND([move_domain, additional_domain]),
            fields=['id', 'date', 'move_id', 'is_storno', 'account_id', 'debit', 'credit', 'balance', 'partner_id'],
            order='date,id',
        )
        _make_bank_storno(data_lines, vendor)
        summ = start_sum
        for line in data_lines:
            line_summ = summ + line['balance']
            last_credit = 0
            last_debit = 0
            if summ < 0:
                last_credit = - summ
            elif summ > 0:
                last_debit = summ

            current_credit = 0
            current_debit = 0

            if line_summ < 0:
                current_credit = -line_summ
            elif line_summ > 0:
                current_debit = line_summ

            if vendor:
                first_event = current_debit - last_debit + line['credit']
            else:
                first_event = current_credit - last_credit + line['debit']
            ret.append({
                'id': line['id'],
                'date': line['date'],
                'amount_first_event': first_event,
            })
            summ = line_summ

        return ret

    #TODO need close period optimisation
    @api.model
    def _calc_first_event_by_move_line(self, move_line):
        if not move_line.account_id.first_event:
            return None
        vendor = move_line.account_id.account_type == 'liability_payable'
        partner = move_line.move_id.partner_id
        company = move_line.move_id.company_id

        if not partner or (vendor and partner and partner.vat_non_payer):
            return None

        events = []

        tracking = partner.tracking_first_event_vendor if vendor else partner.tracking_first_event

        if tracking == 'in_general':
            events = self.env['account.vat.calculations']._calc_first_event(
                [
                    ('partner_id', '=', partner.id),
                ],
                vendor=vendor,
            )

        elif tracking == 'by_order':
            if vendor:
                po_id = self.get_po_id_from_move_line(move_line)
                if po_id:
                    move_lines = self.get_move_line_ids_by_po_id(po_id)
                    events = self.env['account.vat.calculations']._calc_first_event(
                        [
                            ('id', 'in', move_lines),
                        ],
                        vendor=vendor,
                    )
                else:
                    move_lines = self.get_move_line_ids_empty_po_id(partner.id, company.id)
                    events = self.env['account.vat.calculations']._calc_first_event(
                        [
                            ('id', 'in', move_lines),
                        ],
                        vendor=vendor,
                    )
            else:
                so_id = self.get_so_id_from_move_line(move_line)
                if so_id:
                    move_lines = self.get_move_line_ids_by_so_id(so_id)
                    events = self.env['account.vat.calculations']._calc_first_event(
                        [
                            ('id', 'in', move_lines),
                        ],
                        vendor=vendor,
                    )
                else:
                    move_lines = self.get_move_line_ids_empty_so_id(partner.id, company.id)
                    events = self.env['account.vat.calculations']._calc_first_event(
                        [
                            ('id', 'in', move_lines),
                        ],
                        vendor=vendor,
                    )

        elif tracking == 'by_contract':
            contract_id = self.get_contract_id_from_move_line(move_line)
            if contract_id:
                move_lines = self.get_move_line_ids_by_contract_id(contract_id)
                events = self.env['account.vat.calculations']._calc_first_event(
                    [
                        ('id', 'in', move_lines),
                    ],
                    vendor=vendor,
                )
            else:
                move_lines = self.get_move_line_ids_without_contract_id(partner.id, move_line.company_id.id)
                events = self.env['account.vat.calculations']._calc_first_event(
                    [
                        ('id', 'in', move_lines),
                    ],
                    vendor=vendor,
                )

        for event in events:
            if event['id'] == move_line.id:
                return event

        return None
