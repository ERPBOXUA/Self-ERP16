from odoo import api, models, _
from odoo.tools.float_utils import float_is_zero


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def action_open_contract(self, options, params):
        dummy, record_id = self.env['account.report']._get_model_info_from_id(params['id'])

        if record_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.contract',
                'res_id': record_id,
                'views': [[False, 'form']],
                'view_mode': 'form',
                'target': 'current',
            }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['groupby_contract'] = (previous_options or {}).get('groupby_contract', False)

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        groupby_contract = options.get('groupby_contract', False)

        # select all lines if group by contract switched on
        if groupby_contract and not self._context.get('print_mode'):
            self = self.with_context(print_mode=True)

        # call super to get result
        result = super(PartnerLedgerCustomHandler, self)._report_expand_unfoldable_line_partner_ledger(
            line_dict_id,
            groupby,
            options,
            progress,
            offset,
            unfold_all_batch_data=unfold_all_batch_data,
        )

        # modify lines in result if group by contract switched on
        if groupby_contract:
            AccountReport = self.env['account.report']
            force_expand_contracts_ids = self._context.get('force_expand_contracts_ids')

            # filter lines with values
            lines_initial = []
            lines = []
            lines_total = []
            for line in result['lines']:
                markup, record_model, record_id = AccountReport._parse_line_id(line.get('id'))[-1]
                if markup == 'initial':
                    lines_initial.append(line)
                elif markup == 'total':
                    lines_total.append(line)
                else:
                    lines.append(line)

            # map all info by contracts
            contracts = self._create_contract_info(line_dict_id, lines, options)

            # create new lines collection
            new_lines = []
            for contract_info in contracts:
                contract_line_id = contract_info.get('contract_line_id')

                columns_metadata = contract_info['columns_metadata']
                columns_initial = contract_info['columns_initial']
                columns_values = contract_info['columns_values']
                for i, column in columns_metadata.items():
                    columns_values[i]['name'] = AccountReport.format_value(
                        columns_values[i]['no_format'],
                        figure_type=column['figure_type'],
                        blank_if_zero=column['blank_if_zero'],
                    )
                    columns_initial[i]['name'] = AccountReport.format_value(
                        columns_initial[i]['no_format'],
                        figure_type=column['figure_type'],
                        blank_if_zero=column['blank_if_zero'],
                    )

                unfolded = contract_line_id in options['unfolded_lines']

                new_lines.append({
                    'id': contract_line_id,
                    'parent_id': line_dict_id,
                    'name': contract_info['name'],
                    'class': 'text',
                    'name_class': 'o_selferp_contract_settlement_line_name',
                    'columns': columns_values,
                    'level': 3,             # Use level=3 (not a 2 or 4) to get tab from partner and to move lines
                    'unfoldable': True,
                    'unfolded': unfolded or options['unfold_all'],
                    'expand_function': '_report_expand_unfoldable_line_contract',

                    # caret_options for this level can not be used because
                    # in this case fold/unfold functionality does not work,
                    # so ve have to use another field to separate contracts
                    # and move lines/payments
                    # 'caret_options': AccountContract._name,
                    'is_contract': True,
                })

                # add initial balance and lines (if unfold contract mode)
                if force_expand_contracts_ids and contract_info['id'] in force_expand_contracts_ids:
                    if any([
                        not float_is_zero((r or {}).get('no_format') or 0.0, precision_rounding=self.env.company.currency_id.rounding)
                        for r in columns_initial
                    ]):
                        new_lines.append({
                            'id': AccountReport._get_generic_line_id(
                                None,
                                None,
                                parent_line_id=contract_line_id,
                                markup='initial',
                            ),
                            'parent_id': contract_line_id,
                            'class': 'o_account_reports_initial_balance',
                            'name': _("Initial Balance"),
                            'name_class': 'o_selferp_contract_settlement_initial_line_name',
                            'columns': columns_initial,
                            'level': 3,
                            'unfoldable': False,
                        })

                    new_lines += contract_info['lines']

            # replace result
            result['lines'] = (
                lines_initial +
                new_lines +
                lines_total
            )

        # return complete result
        return result

    def _report_expand_unfoldable_line_contract(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        result = {
            'lines': [],
            'has_more': False,
        }

        # analyze current options
        groupby_contract = options.get('groupby_contract', False)
        unfolded = line_dict_id in options['unfolded_lines'] or options['unfold_all']

        if groupby_contract and unfolded:
            # extract line IDs
            parent_line_id = line_dict_id[:line_dict_id.rindex('|')]
            dummy, record_id = self.env['account.report']._get_model_info_from_id(line_dict_id)

            # get expanded partner info
            expanded_partner = self.with_context(force_expand_contracts_ids=[record_id])._report_expand_unfoldable_line_partner_ledger(
                parent_line_id,
                groupby,
                options,
                progress,
                0,
                unfold_all_batch_data=None,
            )

            # extract contract lines
            lines = list(filter(lambda r: r['parent_id'] == line_dict_id, expanded_partner['lines']))

            # update lines
            result['lines'] = lines

        return result

    def _create_contract_info(self, parent_line_id, lines, options):
        AccountContract = self.env['account.contract']
        AccountMoveLine = self.env['account.move.line']
        AccountReport = self.env['account.report']
        force_expand_contracts_ids = self._context.get('force_expand_contracts_ids')

        #
        # Get extra-data for move lines
        #
        move_lines_by_id = {}
        for line in lines:
            if line.get('caret_options') == AccountMoveLine._name:
                dummy, record_id = AccountReport._get_model_info_from_id(line.get('id'))
                move_lines_by_id[record_id] = line

        # Get contracts info for move lines and map by line ID
        if move_lines_by_id:
            move_lines_domain = [('id', 'in', list(move_lines_by_id.keys()))]
            if force_expand_contracts_ids is not None:
                move_lines_domain += [('contract_id', 'in', force_expand_contracts_ids)]

            move_lines_info = {
                move_lines_by_id.get(r['id'])['id']: r
                for r in AccountMoveLine.search_read(
                    domain=move_lines_domain,
                    fields=['contract_id'],
                )
                if r['id'] in move_lines_by_id
            }

        # Collect and map all lines by contract ID.
        # Add not move lines item as a sub-lines of None contract line.
        # Make cycle by lines to save order of lines.
        lines_by_contract = {}
        for line in lines:
            contract_id = None
            if line.get('caret_options') == AccountMoveLine._name:
                move_line = move_lines_info.get(line.get('id'))
                if not move_line:
                    continue
                contract_id = move_line['contract_id'] and move_line['contract_id'][0] or None

            if contract_id in lines_by_contract:
                lines_by_contract[contract_id].append(line)
            else:
                lines_by_contract[contract_id] = [line]

        #
        # Create contracts info with initial balances
        #
        dummy, partner_id = AccountReport._get_model_info_from_id(parent_line_id)
        contracts = self._get_contract_with_initial_balances(
            partner_id,
            list(lines_by_contract.keys()),
            options,
        )

        #
        # Fill contract lines
        #
        for contract_info in contracts:
            contract_id = contract_info['id']
            contract_line_id = AccountReport._get_generic_line_id(
                AccountContract._name,
                contract_id,
                parent_line_id=parent_line_id,
            )
            contract_info['contract_line_id'] = contract_line_id

            # iterate over all lines (if exists)
            contract_lines = lines_by_contract.get(contract_id)
            if contract_lines:
                for line in contract_lines:
                    record_model_name, record_id = AccountReport._get_model_info_from_id(line.get('id'))
                    line.update({
                        'id': AccountReport._get_generic_line_id(
                            record_model_name,
                            record_id,
                            parent_line_id=contract_line_id,
                        ),
                        'parent_id': contract_line_id,
                        'level': 4,
                    })

                    columns_metadata = contract_info['columns_metadata']
                    columns_values = contract_info['columns_values']
                    debit = 0.0
                    credit = 0.0
                    for i, column in columns_metadata.items():
                        line_columns = line['columns'][i] or {}
                        line['columns'][i] = line_columns
                        line_value = line_columns.get('no_format') or 0.0
                        expression_label = column.get('expression_label')

                        if expression_label == 'debit':
                            # remember current line debit
                            debit = line_value
                        elif expression_label == 'credit':
                            # remember current line credit
                            credit = line_value

                        if expression_label == 'balance':
                            # compute balance and set it to current line and contract
                            # (there is an important moment: debit and credit columns
                            # must be before balance)
                            line_balance = (columns_values[i].get('no_format') or 0.0) + debit - credit
                            line_columns['no_format'] = line_balance
                            line_columns['name'] = AccountReport.format_value(
                                line_columns['no_format'],
                                figure_type=column['figure_type'],
                                blank_if_zero=column['blank_if_zero'],
                            )
                            columns_values[i]['no_format'] = line_balance
                        else:
                            # just increment value if it's not balance column
                            columns_values[i]['no_format'] += line_value

                    contract_info['lines'].append(line)

        # Sort by contract
        contracts = sorted(contracts, key=lambda r: (r['id'] and 1 or 1000, r['name']))

        # Return prepared contract lines
        return contracts

    def _get_contract_with_initial_balances(self, partner_id, contract_ids, options):
        initial_balances = self._get_contract_initial_balances(partner_id, contract_ids, options)

        # Get additional contract info and map by contract ID
        contract_ids = list(set((contract_ids or []) + list(initial_balances.keys())))
        contracts_info = {
            r['id']: r['display_name']
            for r in self.env['account.contract'].search_read(
                domain=[('id', 'in', contract_ids)],
                fields=['name', 'display_name']
            )
        }

        # Compute values for all contracts
        report = self._get_report_instance(options)
        options_per_column_group = report._split_options_per_column_group(options)

        contracts = []

        for contract_id in contract_ids:
            balances = initial_balances.get(contract_id) or {}
            columns_metadata = {}
            columns_initial = []
            columns_values = []

            column_index = 0
            for column_group_key, column_group_options in options_per_column_group.items():
                column_group_value = balances.get(column_group_key) or {}

                for column in column_group_options['columns']:
                    expression_label = column.get('expression_label')
                    if expression_label in ('debit', 'credit', 'balance'):
                        columns_metadata[column_index] = column

                        initial_value = column_group_value.get(expression_label) or 0.0
                        columns_initial.append({
                            'name': '',
                            'no_format': initial_value,
                            'class': 'number',
                        })
                        columns_values.append({
                            'name': '',
                            'no_format': initial_value,
                            'class': 'number',
                        })
                    else:
                        columns_initial.append({})
                        columns_values.append({})

                    column_index += 1

            contracts.append({
                'id': contract_id,
                'name': contract_id and contracts_info[contract_id] or _("Undefined"),
                'lines': [],
                'columns_metadata': columns_metadata,
                'columns_initial': columns_initial,
                'columns_values': columns_values,
                'initial_debit': balances.get('debit') or 0.0,
                'initial_credit': balances.get('credit') or 0.0,
                'initial_balance': balances.get('balance') or 0.0,
            })

        return contracts

    def _get_contract_initial_balances(self, partner_id, contract_ids, options):
        report = self._get_report_instance(options)

        queries = []
        params = []

        ct_query = self.env['res.currency']._get_query_currency_table(options)
        options_per_column_group = report._split_options_per_column_group(options)

        for column_group_key, column_group_options in options_per_column_group.items():
            new_options = self._get_options_initial_balance(column_group_options)
            tables, where_clause, where_params = report._query_get(
                new_options,
                'normal',
                domain=[('partner_id', '=', partner_id)],
            )

            params.append(column_group_key)
            params += where_params

            queries.append(f'''
                SELECT account_move_line.contract_id,
                       %s                                                                                    as column_group_key,
                       sum(round(account_move_line.debit * currency_table.rate, currency_table.precision))   as debit,
                       sum(round(account_move_line.credit * currency_table.rate, currency_table.precision))  as credit,
                       sum(round(account_move_line.balance * currency_table.rate, currency_table.precision)) as balance
                  FROM {tables}
                  LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
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

    @api.model
    def _get_report_instance(self, options):
        return options and self.env['account.report'].browse(options.get('report_id')) or self.env.ref('account_reports.partner_ledger_report')
