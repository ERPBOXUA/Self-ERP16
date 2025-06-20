from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """ Returns the data required for the invoices & payments matching of partners/accounts (list of dicts).
            If no res_ids is passed, returns data for all partners/accounts that can be reconciled.

            @TODO: REVIEW AND REFACTOR THIS METHOD !!!

            :param res_type: either 'partner' or 'account'
            :param res_ids: ids of the partners/accounts to reconcile, use None to fetch data indiscriminately
                of the id, use [] to prevent from fetching any data at all.
            :param account_type: if a partner is both customer and vendor, you can use 'liability_payable' to reconcile
                the vendor-related journal entries and 'receivable' for the customer-related entries.
        """

        is_vat_invoice = self._context.get('vat_invoice') or False
        if not is_vat_invoice:
            return super().get_data_for_manual_reconciliation(res_type, res_ids=res_ids, account_type=account_type)

        if account_type not in ('liability_payable', 'asset_receivable', None):
            raise UserError(_("Wrong account type, only receivable/payable accounts are acceptable in reconciliation of VAT documents."))

        aml_ids = self._context.get('active_ids') and self._context.get('active_model') == 'account.move.line' and self._context.get('active_ids') or []
        if not aml_ids:
            return []

        aml_ids = tuple(aml_ids)

        Account = self.env['account.account']
        Partner = self.env['res.partner']
        AccountMoveLine = self.env['account.move.line']

        AccountMoveLine.flush_model()
        Account.flush_model()

        self.env.cr.execute('''
            SELECT l.id AS move_line_id,
                   p.id AS partner_id,
                   p.name AS partner_name,
                   a.id AS account_id,
                   l.write_date AS max_date
              FROM account_move_line AS l
                   RIGHT JOIN account_account a ON (a.id = l.account_id)
                   RIGHT JOIN res_partner p ON (l.partner_id = p.id)
             WHERE l.id IN %s
             GROUP BY l.partner_id, 
                      p.id, 
                      a.id, 
                      l.id, 
                      p.last_time_entries_checked
             ORDER BY p.last_time_entries_checked
        ''', (aml_ids,))

        rows = self.env.cr.dictfetchall()

        # Apply ir_rules by filtering out
        ids = [x['partner_id'] for x in rows]
        allowed_ids = set(Partner.browse(ids).ids)
        rows = [row for row in rows if row['partner_id'] in allowed_ids]

        ids = [x['account_id'] for x in rows]
        allowed_ids = set(Account.browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]

        # Keep mode for future use in JS
        mode = 'customers' if account_type == 'asset_receivable' else 'suppliers'

        def _check_not_exact_proposition(account_id, partner_id):
            if account_id and partner_id:
                rec_account = Account.browse(account_id)
                if rec_account and rec_account.reconcile:
                    domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id)
                    recs_count = AccountMoveLine.search_count(domain)
                    return recs_count > 0
            return False

        # Fetch other data
        for row in rows:
            row['reconciliation_proposition'] = []

            account = Account.browse(row['account_id'])
            if account:
                row.update({
                    'account_code': account.code,
                    'account_name': account.name,
                })

                if account.reconcile:
                    currency = account.currency_id or account.company_id.currency_id
                    row['currency_id'] = currency.id
                    move_line_id = row.get('move_line_id')
                    if move_line_id:
                        move_line = AccountMoveLine.browse(move_line_id)
                        if (
                            move_line
                            and move_line.move_id
                            and move_line.move_id.state == 'posted'
                            and (
                                (mode == 'suppliers' and account == move_line.company_id.vat_account_unconfirmed_credit_id)
                                or (mode == 'customers' and account == move_line.company_id.vat_account_unconfirmed_id)
                            )
                            and not float_is_zero(move_line.balance, precision_rounding=currency.rounding)
                        ):
                            rec_prop = self._get_move_line_reconciliation_proposition_for_vat_invoice(move_line, aml_model=AccountMoveLine)
                            row['reconciliation_proposition'] = self._prepare_move_lines(rec_prop, target_currency=currency)
                            row['mode'] = mode
                            row['company_id'] = account.company_id.id
                            row['reconcilable'] = True

        return [
            row for row in rows
            if row['reconciliation_proposition'] or (row.get('reconcilable') and _check_not_exact_proposition(row.get('account_id'), row.get('partner_id')))
        ]

    @api.model
    def _get_move_line_reconciliation_proposition_for_vat_invoice(self, move_line, aml_model=None):
        aml_model = aml_model or self.env['account.move.line']

        if move_line:
            ir_rules_query = aml_model._where_calc([])
            aml_model._apply_ir_rules(ir_rules_query, 'read')
            from_clause, where_clause, where_clause_params = ir_rules_query.get_sql()
            where_str = where_clause and (' WHERE %s' % where_clause) or ''

            tax_group = move_line.vat_invoice_tax_id and move_line.vat_invoice_tax_id.tax_group_id or None
            tax_group_clause = 'tax.tax_group_id = %s' % tax_group.id if tax_group else 'tax.tax_group_id IS NULL'

            query = '''
                SELECT aml.id
                  FROM account_move_line AS aml
                       LEFT JOIN account_move AS am ON am.id = aml.move_id
                       LEFT JOIN account_account AS aa ON aa.id = aml.account_id
                       LEFT JOIN account_tax AS tax ON tax.id = aml.vat_invoice_tax_id
                 WHERE am.id != {source_move_id}
                       AND am.state = 'posted'
                       AND aa.reconcile = TRUE
                       AND aml.id != {source_line_id}
                       AND NOT aml.reconciled
                       AND aml.amount_residual = {amount}  
                       AND aml.partner_id = {partner_id}   
                       AND {vat_tax_clause}
                       AND aml.id IN (SELECT account_move_line.id FROM {security_params})
                 ORDER BY aml.date desc
                 LIMIT 1    
            '''.format(
                amount='%.2f' % -move_line.amount_residual,
                partner_id=move_line.partner_id.id,
                source_move_id=move_line.move_id.id,
                source_line_id=move_line.id,
                vat_tax_clause=tax_group_clause,
                security_params=from_clause + where_str,
            )

            self.env.cr.execute(query, where_clause_params)

            data = self.env.cr.fetchall()
            if data:
                proposition_line_id = data[0][0]
                return move_line | aml_model.browse(proposition_line_id)

        return aml_model
