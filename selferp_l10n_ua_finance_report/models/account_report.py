import re

from ast import literal_eval
from collections import defaultdict

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import get_lang


CUSTOM_ENGINE_GROUPED_BY_PARTNER_REGEX = re.compile(
    r'(?P<agg_formula>(sum_|sum_if_pos_|sum_if_neg_))(?P<account_code>\d{6})'
)


class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_product = fields.Boolean(
        string="Products",
        compute=lambda x: x._compute_report_option_filter('filter_product'),
        readonly=False,
        store=True,
        depends=['root_report_id'],
    )

    def _init_options_product(self, options, previous_options=None):
        if not self.filter_product:
            return

        options['product'] = True
        previous_product_ids = previous_options and previous_options.get('product_ids') or []
        options['product_categories'] = previous_options and previous_options.get('product_categories') or []

        selected_products = self.env['product.product'].search([('id', 'in', previous_product_ids)])
        options['selected_product_ids'] = selected_products.mapped('name')
        options['product_ids'] = selected_products.ids

        selected_product_categories = self.env['product.category'].browse(options['product_categories'])
        options['selected_product_categories'] = selected_product_categories.mapped('name')

    @api.model
    def _get_options_product_domain(self, options):
        domain = []
        if options.get('product_ids'):
            domain.append(('product_id', 'in', options['product_ids']))
        if options.get('product_categories'):
            domain.append(('product_id.categ_id', 'child_of', options['product_categories']))
        return domain

    def _get_options_domain(self, options, date_scope):
        domain = super()._get_options_domain(options, date_scope)

        domain += self._get_options_product_domain(options)

        return domain

    def _get_expression_audit_aml_domain(self, expression_to_audit, options):
        if expression_to_audit.engine == 'custom':
            if expression_to_audit.formula == '_report_custom_engine_grouped_by_partner':
                parsed_subformula = CUSTOM_ENGINE_GROUPED_BY_PARTNER_REGEX.match(expression_to_audit.subformula).groupdict()

                result_by_partner = self._report_custom_engine_grouped_by_partner(
                    expression_to_audit,
                    options,
                    expression_to_audit.date_scope,
                    'partner_id',
                    None,
                )

                return [
                    '&',
                    ('account_id.code', '=', parsed_subformula['account_code']),
                    ('partner_id', 'in', tuple(r[0] for r in result_by_partner)),
                ]

        return super()._get_expression_audit_aml_domain(expression_to_audit, options)

    def _report_custom_engine_grouped_by_partner(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        ct_query = self.env['res.currency']._get_query_currency_table(options)

        result = []
        result_sum = {}
        for expression in expressions:
            parsed_subformula = CUSTOM_ENGINE_GROUPED_BY_PARTNER_REGEX.match(expression.subformula).groupdict()

            if parsed_subformula['agg_formula'] == 'sum_if_pos_':
                having_agg_formula = 'HAVING SUM(account_move_line.balance) > 0'
            elif parsed_subformula['agg_formula'] == 'sum_if_neg_':
                having_agg_formula = 'HAVING SUM(account_move_line.balance) < 0'
            else:
                having_agg_formula = ''

            line_domain = [('account_id.code', '=', parsed_subformula['account_code'])]

            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)
            tail_query, tail_params = self._get_engine_query_tail(offset, limit)

            query = f'''
                SELECT COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                       account_move_line.partner_id AS grouping_key
                  FROM {tables}
                  JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                 WHERE {where_clause}
                 GROUP BY account_move_line.partner_id
                {having_agg_formula}
                {tail_query}
            '''

            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            if current_groupby:
                result = [
                    (query_res.get('grouping_key', None), {expression.subformula: query_res['sum']})
                    for query_res in all_query_res
                ]
            else:
                result_sum.update({expression.subformula: sum(query_res['sum'] for query_res in all_query_res)})

        return result if current_groupby else result_sum

    @staticmethod
    def _report_custom_engine_get_code_line(expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        return {v.subformula: int(v.subformula[1:]) for v in expressions}

    def _report_custom_engine_grouped_by_product(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
    ):
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        product_uom_query = ''
        grouping_key_query = ''
        join_product = '''
            JOIN account_move ON account_move.id = account_move_line.move_id
            LEFT JOIN stock_move ON stock_move.id = account_move.stock_move_id
        '''
        group_by_query = ''
        if current_groupby == 'product_id':
            lang = self.env.user.lang or get_lang(self.env).code
            product_uom_query = f", COALESCE(uom_uom.name->>'{lang}', uom_uom.name->>'en_US') AS product_uom"
            join_product += '''
                JOIN product_product ON product_product.id = account_move_line.product_id
                JOIN product_template ON product_template.id = product_product.product_tmpl_id
                JOIN uom_uom ON uom_uom.id = product_template.uom_id
            '''
            grouping_key_query = f', account_move_line.{current_groupby} AS grouping_key'
            group_by_query = f' GROUP BY account_move_line.{current_groupby}, product_template.id, uom_uom.id'
        elif current_groupby:
            grouping_key_query = f', {current_groupby} AS grouping_key'
            group_by_query = f' GROUP BY {current_groupby}'

        line_domain = [('account_type', '=', 'asset_current')]
        tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        tail_query, tail_params = self._get_engine_query_tail(offset, limit)

        query = f'''
            SELECT COALESCE(SUM(CASE WHEN account_move_line.balance > 0 THEN stock_move.product_qty ELSE -stock_move.product_qty END), 0.00) AS qty,
                   COALESCE(SUM(CASE WHEN account_move_line.balance > 0 THEN stock_move.product_qty ELSE 0 END), 0.00) AS qty_if_pos,
                   COALESCE(SUM(CASE WHEN account_move_line.balance < 0 THEN stock_move.product_qty ELSE 0 END), 0.00) AS qty_if_neg
                   {product_uom_query}
                   {grouping_key_query}
              FROM {tables}
              JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
              {join_product}
             WHERE {where_clause}
            {group_by_query}
            {tail_query}
        '''

        self._cr.execute(query, where_params + tail_params)
        all_query_res = self._cr.dictfetchall()

        if current_groupby:
            return [
                (
                    query_res.get('grouping_key', None),
                    {
                        'product_uom': query_res.get('product_uom'),
                        'qty': query_res.get('qty') or '',
                        'qty_if_pos': query_res.get('qty_if_pos') or '',
                        'qty_if_neg': -query_res.get('qty_if_neg') or '',
                    },
                )
                for query_res in all_query_res
            ]
        else:
            return {
                'product_uom': '',
                'qty': sum(query_res.get('qty') for query_res in all_query_res),
                'qty_if_pos': sum(query_res.get('qty_if_pos') for query_res in all_query_res),
                'qty_if_neg': -sum(query_res.get('qty_if_neg') for query_res in all_query_res),
            }

    def action_audit_cell(self, options, params):
        action = super().action_audit_cell(options, params)

        if action['res_model'] == 'account.move.line':
            action['view_mode'] = 'list,form'
            action['views'].append((False, 'form'))

        return action
