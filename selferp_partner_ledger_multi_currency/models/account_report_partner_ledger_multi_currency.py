from collections import defaultdict

from odoo import api, models, fields, _
from odoo.tools import float_compare
from odoo.tools.misc import format_date


class AccountReportPartnerLedgerMultiCurrencyHandler(models.AbstractModel):
    _name = 'account.report.partner_ledger.multi_currency.handler'
    _inherit = 'account.partner.ledger.report.handler'
    _description = "Partner Ledger Multi Currency Report Handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # force non-company currency records only
        options['forced_domain'] = self._get_forced_domain(options, [
            ('currency_id', '!=', False),
            ('currency_id', '!=', self.env.company.currency_id.id),
            ('amount_currency', '!=', 0),
        ])

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals)

        # remove last grand total line
        if lines:
            lines = lines[:-1]

        return lines

    def _query_partners(self, options):
        """ Just get partners info without totals

        :param options:
        :return:
        """
        report = self._get_report_instance(options)

        # get all partners where moves exists
        tables, where_clause, where_params = report._query_get(options, 'normal')
        query = f'''
            SELECT account_move_line.partner_id
              FROM {tables}
             WHERE {where_clause}
             GROUP BY account_move_line.partner_id
        '''

        self._cr.execute(query, where_params)
        partner_ids = [r[0] for r in self._cr.fetchall()]

        # Retrieve the partners to browse
        # Note a search is done instead of a browse to preserve the table ordering.
        partners = self.env['res.partner'].with_context(active_test=False).search([('id', 'in', partner_ids)])

        # Add 'Partner Unknown' if needed
        if None in partner_ids:
            partners = [p for p in partners] + [None]

        # return partners (with empty column values)
        return [(partner, {}) for partner in partners]

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # just call super for get super result (by contract or partner)
        if self.env.context.get('selferp_skip_partner_ledger_multi_currency'):
            return super()._report_expand_unfoldable_line_partner_ledger(
                line_dict_id,
                groupby,
                options,
                progress,
                offset,
                unfold_all_batch_data=unfold_all_batch_data,
            )

        # else - totally override method to group by currencies
        report = self._get_report_instance(options)
        model, partner_id = report._get_model_info_from_id(line_dict_id)

        lines = []

        # get currencies
        currency_data = self._get_currency_sums(
            report,
            options,
            'strict_range',
            domain=[('partner_id', '=', partner_id)],
        )

        if currency_data:
            currency_ids = list(currency_data.keys())
            # use search instead of browse to preserve order
            currencies = self.env['res.currency'].with_context(active_test=False).search([('id', 'in', currency_ids)])

            # get initial balances for all currencies
            initial_balances = self._get_currency_sums(
                report,
                self._get_options_initial_balance(options),
                'strict_range',
                domain=[('partner_id', '=', partner_id), ('currency_id', 'in', currency_ids)],
            )

            for currency in currencies:
                # build currency line ID
                currency_line_id = report._get_generic_line_id(
                    currency._name,
                    currency.id,
                    parent_line_id=line_dict_id,
                )

                # fill columns by currency (initial balance + balance)
                columns = []
                for column in options['columns']:
                    expression_label = column.get('expression_label')
                    if expression_label in ('debit', 'credit', 'balance'):
                        col_value = (initial_balances[currency.id].get(expression_label) or 0) + (currency_data[currency.id].get(expression_label) or 0)
                        columns.append({
                            'name': report.format_value(col_value, currency=currency, figure_type=column['figure_type'], blank_if_zero=False),
                            'no_format': col_value,
                            'class': 'number',
                        })
                    else:
                        columns.append({})

                # add currency main line
                lines.append({
                    'id': currency_line_id,
                    'parent_id': line_dict_id,
                    'name': currency.name,
                    'class': 'o_selferp_currency_line text',
                    'name_class': 'o_selferp_currency_line_name ',
                    'columns': columns,
                    'level': 3,
                    'unfoldable': True,
                    'unfolded': options['unfold_all'] or currency_line_id in options['unfolded_lines'],
                    'expand_function': '_report_expand_unfoldable_line_currency',

                    # caret_options for this level can not be used because
                    # in this case fold/unfold functionality does not work,
                    # so ve have to use another field to separate this line
                    # and move lines/payments
                    'is_currency': True,
                })

        # return results
        return {
            'lines': lines,
            'has_more': False,
        }

    def _report_expand_unfoldable_line_contract(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self._get_report_instance(options)

        line_ids = line_dict_id.split('|')
        model, currency_id = report._get_model_info_from_id(line_ids[-2])

        # skip currency logic for this report
        self = self.with_context(selferp_skip_partner_ledger_multi_currency=True)

        # filter by currency
        parent_line_id = '|'.join(line_ids[:-2] + line_ids[-1:])
        new_options = dict(
            options,
            forced_domain=self._get_forced_domain(options, [('currency_id', '=', currency_id)]),
            unfolded_lines=(options.get('unfolded_lines') or []) + [parent_line_id],
        )

        # get lines with super
        result = super(AccountReportPartnerLedgerMultiCurrencyHandler, self)._report_expand_unfoldable_line_contract(
            parent_line_id,
            groupby,
            new_options,
            progress,
            offset,
            unfold_all_batch_data=unfold_all_batch_data,
        )

        # modify parent in result lines
        self._fix_currency_inned_lines(result['lines'], options, currency_id, line_dict_id)

        # return result
        return result

    def _report_expand_unfoldable_line_currency(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        result_lines = []
        result = {
            'lines': result_lines,
            'has_more': False,
        }

        # analyze current options
        unfolded = line_dict_id in options['unfolded_lines'] or options['unfold_all']

        if unfolded:
            # extract line IDs
            separator = line_dict_id.rindex('|')
            parent_line_id = line_dict_id[:separator]
            dummy, parent_record_id = self.env['account.report']._get_model_info_from_id(parent_line_id)
            dummy, currency_id = self.env['account.report']._get_model_info_from_id(line_dict_id)
            currency = self.env['res.currency'].with_context(active_test=False).browse(currency_id)

            # get initial balance line
            report = self._get_report_instance(options)
            initial_balances = self._get_currency_sums(
                report,
                self._get_options_initial_balance(options),
                'strict_range',
                domain=[('partner_id', '=', parent_record_id), ('currency_id', '=', currency_id)],
            )
            columns_initial = []
            for column in options['columns']:
                expression_label = column.get('expression_label')
                if expression_label in ('debit', 'credit', 'balance'):
                    col_value = initial_balances[currency_id].get(expression_label) or 0
                    columns_initial.append({
                        'name': report.format_value(
                            col_value,
                            currency=currency,
                            figure_type=column['figure_type'],
                            blank_if_zero=False,
                        ),
                        'no_format': col_value,
                        'class': 'number',
                    })
                else:
                    columns_initial.append({})

            result_lines.append({
                'id': report._get_generic_line_id(
                    None,
                    None,
                    parent_line_id=line_dict_id,
                    markup='initial',
                ),
                'parent_id': line_dict_id,
                'class': 'o_account_reports_initial_balance',
                'name': _("Initial Balance"),
                'name_class': 'o_selferp_contract_settlement_initial_line_name',
                'columns': columns_initial,
                'level': 3,
                'unfoldable': False,
            })

            # get inner lines (grouped by contract or partner and skip currency logic override)
            inner_options = self._get_forced_domain_options(options, [('currency_id', '=', currency_id)])
            inner = super(
                AccountReportPartnerLedgerMultiCurrencyHandler,
                self.with_context(selferp_skip_partner_ledger_multi_currency=True, print_mode=True),
            )._report_expand_unfoldable_line_partner_ledger(
                parent_line_id,
                groupby,
                inner_options,
                progress,
                0,
                unfold_all_batch_data=None,
            )

            # update inner lines
            currency_line_id = line_dict_id[separator + 1:]
            lines = inner['lines']
            if lines:
                markup, model, value = report._parse_line_id(lines[0]['id'])[-1]
                if markup == 'initial':
                    # remove partner's initial balance
                    lines = lines[1:]

                # fix inner lines values
                self._fix_currency_inned_lines(lines, options, currency_id, line_dict_id)

            # append inner lines
            result_lines += lines

        # return result
        return result

    def _get_initial_balance_values(self, partner_ids, options):
        report = self._get_report_instance(options)

        queries = []
        params = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(column_group_options)
            tables, where_clause, where_params = report._query_get(
                new_options,
                'normal',
                domain=[('partner_id', 'in', partner_ids)],
            )
            params.append(column_group_key)
            params += where_params
            queries.append(f'''
                SELECT account_move_line.partner_id                                                                                             AS partner_id,
                       %s                                                                                                                       AS column_group_key,
                       COALESCE(SUM(CASE WHEN account_move_line.amount_currency < 0 THEN 0 ELSE account_move_line.amount_currency END), 0)      AS debit,
                       COALESCE(SUM(CASE WHEN account_move_line.amount_currency > 0 THEN 0 ELSE ABS(account_move_line.amount_currency) END), 0) AS credit,
                       COALESCE(SUM(account_move_line.amount_currency), 0)                                                                      AS balance
                FROM {tables}
                WHERE {where_clause}
                GROUP BY account_move_line.partner_id
            ''')
        self._cr.execute(' UNION ALL '.join(queries), params)

        init_balance_by_col_group = {
            partner_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for partner_id in partner_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['partner_id']][result['column_group_key']] = result

        return init_balance_by_col_group

    def _get_contract_initial_balances(self, partner_id, contract_ids, options):
        report = self._get_report_instance(options)

        queries = []
        params = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(column_group_options)
            tables, where_clause, where_params = report._query_get(
                new_options,
                'normal',
                domain=[('partner_id', '=', partner_id)],
            )

            params.append(column_group_key)
            params += where_params

            queries.append(f'''
                SELECT account_move_line.contract_id                                                                                            AS contract_id,
                       %s                                                                                                                       AS column_group_key,
                       COALESCE(SUM(CASE WHEN account_move_line.amount_currency < 0 THEN 0 ELSE account_move_line.amount_currency END), 0)      AS debit,
                       COALESCE(SUM(CASE WHEN account_move_line.amount_currency > 0 THEN 0 ELSE ABS(account_move_line.amount_currency) END), 0) AS credit,
                       COALESCE(SUM(account_move_line.amount_currency), 0)                                                                      AS balance
                  FROM {tables}
                 WHERE {where_clause}
                 GROUP BY account_move_line.contract_id
            ''')

        self._cr.execute(' UNION ALL '.join(queries), params)
        result = {
            r['contract_id']: {
                r['column_group_key']: r,
            }
            for r in self._cr.dictfetchall()
        }

        return result

    def _get_currency_sums(self, report, options, date_scope, domain=None):
        tables, where_clause, where_params = report._query_get(
            options,
            date_scope,
            domain=domain or [],
        )

        query = f'''
            SELECT account_move_line.currency_id                                                                                            AS currency_id,
                   COALESCE(SUM(CASE WHEN account_move_line.amount_currency < 0 THEN 0 ELSE account_move_line.amount_currency END), 0)      AS debit,
                   COALESCE(SUM(CASE WHEN account_move_line.amount_currency > 0 THEN 0 ELSE ABS(account_move_line.amount_currency) END), 0) AS credit,
                   COALESCE(SUM(account_move_line.amount_currency), 0)                                                                      AS balance
              FROM {tables}
             WHERE {where_clause}
             GROUP BY account_move_line.currency_id
        '''

        self._cr.execute(query, where_params)

        result = defaultdict(lambda: defaultdict(lambda: 0))
        result.update({r['currency_id']: r for r in self._cr.dictfetchall()})

        return result

    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        line = super()._get_report_line_partners(options, partner, partner_values, level_shift=level_shift)

        # make partner line always unfoldable
        line['unfoldable'] = True

        # clear totals
        for i, column in enumerate(options['columns']):
            line['columns'][i] = {}

        return line

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        report = self.env['account.report']
        currency = self.env['res.currency'].browse(aml_query_result['currency_id'])

        columns = []

        for column in options['columns']:
            col_expr_label = column['expression_label']

            # get column value
            col_value = None
            if col_expr_label == 'ref':
                col_value = report._format_aml_name(aml_query_result['name'], aml_query_result['ref'], aml_query_result['move_name'])
            elif column['column_group_key'] == aml_query_result['column_group_key']:
                if col_expr_label in ('debit', 'credit', 'balance'):
                    col_value = aml_query_result['amount_currency']
                    if col_expr_label == 'debit' and float_compare(col_value, 0, precision_digits=currency.decimal_places or 2) < 0:
                        col_value = 0
                    elif col_expr_label == 'credit':
                        if float_compare(col_value, 0, precision_digits=currency.decimal_places or 2) > 0:
                            col_value = 0
                        else:
                            col_value = abs(col_value)
                else:
                    col_value = aml_query_result[col_expr_label]

            # format column value
            if col_value is None:
                columns.append({})
            else:
                col_class = 'number'

                if col_expr_label == 'date_maturity':
                    col_class = 'date'
                    formatted_value = format_date(self.env, fields.Date.from_string(col_value))
                elif col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])
                else:
                    if col_expr_label == 'ref':
                        col_class = 'o_account_report_line_ellipsis'
                    elif col_expr_label not in ('debit', 'credit'):
                        col_class = ''
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'])

                columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

        if aml_query_result['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        return {
            'id': report._get_generic_line_id('account.move.line', aml_query_result['id'], parent_line_id=partner_line_id),
            'parent_id': partner_line_id,
            'name': format_date(self.env, aml_query_result['date']),
            'class': 'text-muted' if aml_query_result['key'] == 'indirectly_linked_aml' else 'text',  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 4 + level_shift,
        }

    def _get_report_line_total(self, options, totals_by_column_group):
        # we have not grand total for this report
        return {}

    def _fix_currency_inned_lines(self, lines, options, currency_id, parent_line_id):
        if lines:
            report = self._get_report_instance(options)
            currency = self.env['res.currency'].with_context(active_test=False).browse(currency_id)

            for line in lines:
                # reformat numerical values
                for i, column in enumerate(options['columns']):
                    if column.get('expression_label') in ('debit', 'credit', 'balance'):
                        line['columns'][i]['name'] = report.format_value(
                            line['columns'][i]['no_format'],
                            currency=currency,
                            figure_type=column['figure_type'],
                            blank_if_zero=False,
                        )

                # move line position
                line.update({
                    'id': parent_line_id + '|' + line['id'].split('|')[-1],
                    'parent_id': parent_line_id,
                    'level': line['level'] + 1,
                })

    @api.model
    def _get_forced_domain_options(self, options, add_domain):
        return dict(options, forced_domain=self._get_forced_domain(options, add_domain))

    @api.model
    def _get_forced_domain(self, options, add_domain):
        return (options.get('forced_domain') or []) + (add_domain or [])
