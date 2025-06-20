from datetime import timedelta

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.misc import format_date


COLUMN_NAMES__TOTAL = [
    'debit',
    'credit',
    'balance',
    'amount_first_event',
    'amount_vat_tax',
]

DEFAULT_TOTALS = {total: 0.0 for total in COLUMN_NAMES__TOTAL}


class AccountVATFirstEventReportHandler(models.AbstractModel):
    _name = 'account.report.vat.first_event.handler'
    _inherit = 'account.report.custom.handler'
    _description = "VAT First Event Report Handler"

    def action_open_record(self, options, params):
        record_model, record_id = self.env['account.report']._get_model_info_from_id(params['id'])
        return {
            'type': 'ir.actions.act_window',
            'res_model': record_model,
            'res_id': record_id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def action_open_journal_items(self, options, params):
        params['view_ref'] = 'account.view_move_line_tree_grouped_partner'
        action = self.env['account.report'].open_journal_items(options=options, params=params)
        action.get('context', {}).update({
            'search_default_group_by_account': 0,
            'search_default_group_by_partner': 1,
        })
        return action

    def action_create_vat_invoices(self, options):
        report = self.env.ref('selferp_l10n_ua_vat.account_report_vat_first_event')
        tables, where_clause, where_params = report._query_get(
            options,
            'normal',
            domain=[
                ('vat_invoice_id', '=', False),
            ],
        )

        self.env.cr.execute(f'''
            SELECT DISTINCT partner_id
              FROM {tables}
             WHERE {where_clause}
        ''', where_params)
        partner_ids = [r[0] for r in self.env.cr.fetchall()]

        if not partner_ids:
            raise UserError(_("There are nothing to create VAT invoices"))

        return self._create_vat_invoices(options, partner_ids)

    def action_create_vat_invoices_by_partner(self, options, params):
        record_model, record_id = self.env['account.report']._get_model_info_from_id(params['id'])
        return self._create_vat_invoices(options, [record_id])

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _("Create VAT Invoices"),
            'sequence': 900,
            'action': 'action_create_vat_invoices',
        })

        prev_options = previous_options or {}

        options['partner_account_type'] = prev_options.get('partner_account_type', 'asset_receivable')
        options['tracking_first_event'] = prev_options.get('tracking_first_event', 'by_contract')
        options['groupby_contract'] = (
            options['tracking_first_event'] == 'by_contract'
            and prev_options.get('groupby_contract')
            or False
        )
        options['groupby_sale_order'] = (
            options['tracking_first_event'] == 'by_order'
            and options['partner_account_type'] == 'asset_receivable'
            and prev_options.get('groupby_sale_order')
            or False
        )
        options['groupby_purchase_order'] = (
            options['tracking_first_event'] == 'by_order'
            and options['partner_account_type'] == 'liability_payable'
            and prev_options.get('groupby_purchase_order')
            or False
        )

    def _caret_options_initializer(self):
        caret_options = super()._caret_options_initializer()

        caret_options.update({
            'account.move.line': [
                {
                    'name': _("View Journal Entry"),
                    'action': 'caret_option_open_record_form',
                },
            ],

            'account.move.line:with_vat_invoice': [
                {
                    'name': _("View Journal Entry"),
                    'action': 'caret_option_open_record_form',
                },
                {
                    'name': _("View VAT Invoice"),
                    'action': 'caret_option_open_record_form',
                    'action_param': 'vat_invoice_id',
                },
            ],
            'account.move.line:with_first_event': [
                {
                    'name': _("View Journal Entry"),
                    'action': 'caret_option_open_record_form',
                },
                {
                    'name': _("View First Event Journal Entry"),
                    'action': 'caret_option_open_record_form',
                    'action_param': 'first_event_vat_invoice_id',
                },
            ],
            'account.move.line:with_vat_invoice_and_first_event': [
                {
                    'name': _("View Journal Entry"),
                    'action': 'caret_option_open_record_form',
                },
                {
                    'name': _("View VAT Invoice"),
                    'action': 'caret_option_open_record_form',
                    'action_param': 'vat_invoice_id',
                },
                {
                    'name': _("View First Event Journal Entry"),
                    'action': 'caret_option_open_record_form',
                    'action_param': 'first_event_vat_invoice_id',
                },
            ],
        })

        return caret_options

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        # fix options
        if self.env.context.get('print_mode') and options.get('filter_search_bar'):
            options.setdefault('forced_domain', []).append(('partner_id', 'ilike', options['filter_search_bar']))

        # get all lines
        lines = self._build_lines_all(report, options)

        # convert to dynamic lines
        dynamic_lines = [(0, line) for line in lines]

        return dynamic_lines

    def _get_report_domain(self, report, options, extra_domain=None):
        self.env['account.move.line'].check_access_rights('read')

        domain = report._get_options_domain(options, 'strict_range') + (extra_domain or [])

        forced_domain = options.get('forced_domain')
        if forced_domain:
            domain += forced_domain

        return domain

    def _build_lines_all(self, report, options):
        lines = []

        # get move lines
        domain = self._get_report_domain(report, options)
        move_lines = self.env['account.move.line'].search(domain, order='date, id')

        if move_lines:
            totals = dict(DEFAULT_TOTALS)

            # get partners info
            move_lines_by_partner = {}
            for move_line in move_lines:
                partner = move_line.partner_id
                if partner:
                    partner_move_lines = move_lines_by_partner.get(partner)
                    if not partner_move_lines:
                        partner_move_lines = move_lines.browse()
                    partner_move_lines += move_line
                    move_lines_by_partner[partner] = partner_move_lines

            partners = sorted(list(move_lines_by_partner.keys()), key=lambda r: r.name)

            # get initial balances
            initial_balances = {
                'res.partner': self._get_initial_balances(report, options, 'partner_id'),
            }
            if options['groupby_contract']:
                initial_balances['account.contract'] = self._get_initial_balances(report, options, 'contract_id', 'partner_id')
            if options['groupby_sale_order']:
                initial_balances['sale.order'] = self._get_initial_balances(report, options, 'linked_sale_order_id', 'partner_id')
            if options['groupby_purchase_order']:
                initial_balances['purchase.order'] = self._get_initial_balances(report, options, 'linked_purchase_order_id', 'partner_id')

            # for each partner build lines
            for partner in partners:
                partner_move_lines = move_lines_by_partner.get(partner)

                partner_lines, partner_totals = self._build_lines_by_partner(
                    report,
                    options,
                    partner,
                    partner_move_lines,
                    initial_balances,
                )

                lines += partner_lines
                totals = self._sum_column_totals(totals, partner_totals)

            # add total lines
            lines += self._build_lines_total(report, options, totals)

        return lines

    def _build_lines_by_partner(self, report, options, partner, move_lines, initial_balances):
        partner_lines = []
        partner_totals = dict(DEFAULT_TOTALS)

        # append initial balance
        partner_line_id, partner_initial_balance, partner_line_initial = self._build_lines_initial(
            report,
            options,
            initial_balances['res.partner'],
            partner,
        )
        if partner_line_initial:
            partner_lines += partner_line_initial

        # add move lines grouped by contract/order/nothing
        if options['groupby_contract']:
            partner_lines += self._build_lines_subgroup(
                report,
                options,
                partner_line_id,
                initial_balances['account.contract'].get(partner.id) or {},
                move_lines,
                'contract_id',
                partner_totals,
            )

        elif options['groupby_sale_order']:
            partner_lines += self._build_lines_subgroup(
                report,
                options,
                partner_line_id,
                initial_balances['sale.order'].get(partner.id) or {},
                move_lines,
                'linked_sale_order_id',
                partner_totals,
            )

        elif options['groupby_purchase_order']:
            partner_lines += self._build_lines_subgroup(
                report,
                options,
                partner_line_id,
                initial_balances['purchase.order'].get(partner.id) or {},
                move_lines,
                'linked_purchase_order_id',
                partner_totals,
            )

        else:
            current_balance = partner_initial_balance.get('balance') or 0.0
            partner_lines += self._build_lines_move_line(
                report,
                options,
                partner_line_id,
                move_lines,
                current_balance,
                partner_totals,
            )

        # prepend partner line
        partner_totals = self._sum_column_totals(partner_initial_balance, partner_totals)
        partner_lines = self._build_lines_partner(report, options, partner, partner_line_id, partner_totals, move_lines) + partner_lines

        # return all lines by partner
        return partner_lines, partner_totals

    def _build_lines_partner(self, report, options, partner, partner_line_id, values, move_lines):
        column_values = self._get_column_values(report, options, values)
        move_lines_by_partner = move_lines.filtered(lambda r: r.partner_id == partner)
        if options['partner_account_type'] != 'liability_payable':
            create_vat_invoices_allowed = any(
                [
                    not r.vat_invoice_id and not float_is_zero(r.amount_first_event, precision_rounding=r.currency_id.rounding)
                    for r in move_lines_by_partner
                ]
            )
        else:
            create_vat_invoices_allowed = any(
                [
                    not r.vat_first_event_move_id and not float_is_zero(r.amount_first_event, precision_rounding=r.currency_id.rounding)
                    for r in move_lines_by_partner
                ]
            )

        return [{
            'id': partner_line_id,
            'level': 2,
            'name': (partner.name or '')[:128],
            'columns': column_values,
            'unfoldable': True,
            'unfolded': self._context.get('print_mode') or options.get('unfold_all') or partner_line_id in options['unfolded_lines'],
            'create_vat_invoices_allowed': create_vat_invoices_allowed,
        }]

    def _build_lines_subgroup(self, report, options, parent_line_id, initial_balances, move_lines, group_by, totals):
        lines = []

        # split move lines
        move_lines_with = move_lines.filtered(lambda r: r[group_by])
        move_lines_without = move_lines - move_lines_with

        # get groups
        groups = list(move_lines_with.mapped(group_by).sorted('display_name'))
        if move_lines_without:
            groups.append(move_lines_without[0][group_by])

        for group in groups:
            group_lines = []
            group_totals = dict(DEFAULT_TOTALS)

            # add initial line (if exists)
            group_line_id, group_initial_balance, group_line_initial = self._build_lines_initial(
                report,
                options,
                initial_balances,
                group,
                level_shift=1,
                name_class='o_selferp_contract_settlement_initial_line_name',
            )
            if group_line_initial:
                group_lines += group_line_initial

            # add move lines
            if group:
                group_move_lines = move_lines_with.filtered(lambda r: r[group_by] == group)
            else:
                group_move_lines = move_lines_without
            group_lines += self._build_lines_move_line(
                report,
                options,
                group_line_id,
                group_move_lines,
                group_initial_balance['balance'],
                group_totals,
                level_shift=1,
            )

            # update totals
            totals.update(self._sum_column_totals(totals, group_totals))
            group_totals = self._sum_column_totals(group_initial_balance, group_totals)

            # prepend group line
            column_values = self._get_column_values(report, options, group_totals)
            lines += [{
                'id': group_line_id,
                'parent_id': parent_line_id,
                'name': group.display_name if group else _("Undefined"),
                'class': 'text',
                'name_class': 'o_selferp_contract_settlement_line_name',
                'columns': column_values,
                'level': 3,  # Use level=3 (not a 2) to get tab from partner and same level as move lines
                'unfoldable': True,
                'unfolded': self._context.get('print_mode') or options.get('unfold_all') or group_line_id in options['unfolded_lines'],

                # caret_options for this level can not be used because
                # in this case fold/unfold functionality does not work,
                # so ve have to use another field to separate contracts
                # and move lines/payments
                # 'caret_options': AccountContract._name,
                'is_contract': group._name == 'account.contract',
                'is_sale_order': group._name == 'sale.order',
            }] + group_lines

        # return prepared lines
        return lines

    def _build_lines_initial(self, report, options, initial_balances, record, level_shift=0, name_class=None):
        # get record line ID
        record_line_id = report._get_generic_line_id(record._name, record and record.id or None)

        # get initial balance values
        initial_balance = initial_balances.get(record and record.id or None) or dict(DEFAULT_TOTALS)

        # prepare column values
        column_values = self._get_column_values(report, options, initial_balance)

        # build lines
        lines = None
        if any(column.get('no_format') for column in column_values):
            lines = [{
                'id': report._get_generic_line_id(None, None, parent_line_id=record_line_id, markup='initial'),
                'parent_id': record_line_id,
                'level': 2 + level_shift,
                'class': 'o_account_reports_initial_balance',
                'name': _("Initial Balance"),
                'name_class': name_class or '',
                'columns': column_values,
                'unfoldable': False,
            }]

        # return result
        return record_line_id, initial_balance, lines

    def _build_lines_move_line(self, report, options, parent_line_id, move_lines, current_balance, totals, level_shift=0):
        lines = []

        for move_line in move_lines:
            # change balance
            current_balance += move_line.balance or 0.0

            # change given totals
            for total_column in COLUMN_NAMES__TOTAL:
                totals[total_column] += move_line[total_column] or 0.0

            # prepare column values
            column_values = []

            for column in options['columns']:
                expression_label = column['expression_label']
                col_value = None
                col_class = ''

                if expression_label == 'journal_code':
                    col_value = move_line.journal_id.code
                elif expression_label == 'account_code':
                    col_value = move_line.account_id.code
                else:
                    col_class = 'number'
                    if expression_label == 'amount_first_event' and move_line.vat_invoice_id:
                        col_class += ' text-success'

                    if expression_label == 'balance':
                        col_value = current_balance
                    elif hasattr(move_line, expression_label):
                        col_value = getattr(move_line, expression_label)

                formatted_value = report.format_value(col_value, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])

                column_values.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

            if move_line.vat_invoice_id and move_line.vat_first_event_move_id:
                car_opt = ':with_vat_invoice_and_first_event'
            elif not move_line.vat_invoice_id and move_line.vat_first_event_move_id:
                car_opt = ':with_first_event'
            elif move_line.vat_invoice_id and not move_line.vat_first_event_move_id:
                car_opt = ':with_vat_invoice'
            else:
                car_opt = ''
            # append line
            lines.append({
                'id': report._get_generic_line_id(move_line._name, move_line.id, parent_line_id=parent_line_id),
                'parent_id': parent_line_id,
                'level': 2 + level_shift,
                'class': 'text',
                'name': format_date(self.env, move_line.date),
                'columns': column_values,
                'caret_options': move_line._name + car_opt,
            })

        # return lines
        return lines

    def _build_lines_total(self, report, options, values):
        column_values = self._get_column_values(report, options, values)
        return [{
            'id': report._get_generic_line_id(None, None, markup='total'),
            'level': 1,
            'class': 'total',
            'name': _("Total"),
            'columns': column_values,
        }]

    def _get_initial_balances(self, report, options, group_by, parent_group=None):
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = report._query_get(new_options, 'normal')

        if parent_group:
            self._cr.execute(f'''
                SELECT account_move_line.{parent_group} as {parent_group},
                       account_move_line.{group_by}     as {group_by},
                       sum(account_move_line.debit)     as debit,
                       sum(account_move_line.credit)    as credit,
                       sum(account_move_line.balance)   as balance
                  FROM {tables}
                 WHERE {where_clause}
                 GROUP BY account_move_line.{parent_group},
                          account_move_line.{group_by}
            ''', where_params)
            data = self._cr.dictfetchall()

            result = {}
            for row in data:
                parent = result.get(row[parent_group])
                if not parent:
                    parent = {}
                    result[row[parent_group]] = parent
                parent[row[group_by]] = row

        else:
            self._cr.execute(f'''
                SELECT account_move_line.{group_by}     as {group_by},
                       sum(account_move_line.debit)     as debit,
                       sum(account_move_line.credit)    as credit,
                       sum(account_move_line.balance)   as balance
                  FROM {tables}
                 WHERE {where_clause}
                 GROUP BY account_move_line.{group_by}
            ''', where_params)

            result = {
                r[group_by]: r
                for r in self._cr.dictfetchall()
            }

        return result

    def _get_column_values(self, report, options, values, show_all_numbers=True):
        column_values = []

        for column in options['columns']:
            expression_label = column['expression_label']
            value = values.get(expression_label)

            if expression_label in COLUMN_NAMES__TOTAL:
                if show_all_numbers:
                    blank_if_zero = False
                else:
                    blank_if_zero = column['blank_if_zero']
                formatted_value = report.format_value(value, figure_type=column['figure_type'], blank_if_zero=blank_if_zero)
            else:
                formatted_value = report.format_value(value, figure_type=column['figure_type']) if value else ''

            column_values.append({
                'name': formatted_value,
                'no_format': value,
                'class': 'number',
            })

        return column_values

    def _get_options_initial_balance(self, options):
        new_date_to = fields.Date.from_string(options['date']['date_from']) - timedelta(days=1)
        new_date_options = dict(options['date'], date_from=False, date_to=fields.Date.to_string(new_date_to))
        return dict(options, date=new_date_options)

    def _sum_column_totals(self, *args):
        return {
            column_total: sum([((totals or {}).get(column_total) or 0.0) for totals in args])
            for column_total in COLUMN_NAMES__TOTAL
        }

    def _create_vat_invoices(self, options, partner_ids):
        report = self.env.ref('selferp_l10n_ua_vat.account_report_vat_first_event')
        date_from, date_to, allow_include_initial_balance = report._get_date_bounds_info(options, date_scope='normal')
        vendor = options['partner_account_type'] == 'liability_payable'
        vat_documents = self.env['account.vat.calculations'].generate_vat_documents_by_partners(partner_ids, date_from, date_to, vendor=vendor)

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
        elif vendor:
            action = {
                'name': _("Created first event records"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'views': [[False, 'tree'], [False, 'form']],
            }
            if len(vat_documents) > 1:
                action.update({
                    'domain': [('id', 'in', vat_documents.ids)],
                    'view_mode': 'tree,form',
                })

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
                ]
            }
        else:
            action = self.env.ref('selferp_l10n_ua_vat.account_move_action_vat_invoice').sudo().read()[0]

            if len(vat_documents) > 1:
                action['domain'] = [('id', 'in', vat_documents.ids)]
                return {
                  'type': 'ir.actions.act_multi',
                  'actions': [
                      {'type': 'ir.actions.act_view_reload'},
                      action,
                  ]
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
                  ]
                }



