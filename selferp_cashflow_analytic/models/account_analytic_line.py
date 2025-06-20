from odoo import models, fields, api, _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    account_code = fields.Char(
        string="Account Code",
        related='account_id.code',
        store=True,
        readonly=True,
    )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        result = super().read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy
        )

        if result and 'account_code' in groupby:
            codes = [ln['account_code'] for ln in result if 'account_code' in ln]
            if codes:
                accounts = self.env['account.analytic.account'].search_read(
                    domain=[('code', 'in', codes)],
                    fields=['id', 'code', 'name'],
                )
                accounts = {acc['code']: acc for acc in accounts}

                for group_line in result:
                    if 'account_code' in group_line:
                        self._update_presentation(group_line, accounts)

        return result

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None, readonly_field=None, orderby=None):
        result = super().read_grid(
            row_fields,
            col_field,
            cell_field,
            domain=domain,
            range=range,
            readonly_field=readonly_field,
            orderby=orderby
        )

        if result and 'account_code' in row_fields:
            rows = result.get('rows')
            if rows:
                codes = []
                for r in rows:
                    values = r.get('values')
                    if values and 'account_code' in values:
                        code = values['account_code']
                        # Code can be empty (False) but we use it anyway
                        codes.append(code)

                if codes:
                    accounts = self.env['account.analytic.account'].search_read(
                        domain=[('code', 'in', codes)],
                        fields=['id', 'code', 'name'],
                    )
                    accounts = {acc['code']: acc for acc in accounts}

                    for r in rows:
                        values = r.get('values')
                        if values and 'account_code' in values:
                            self._update_presentation(values, accounts)

        return result

    @staticmethod
    def _update_presentation(data, accounts):
        account_code = data['account_code']
        account = accounts.get(account_code)

        if account:
            account_name = account['name'] or ''
            if not account_code:
                account_code = _("No code")
            caption = '[%s] %s' % (account_code, account_name)
            if caption != data['account_code']:
                data['account_code'] = caption
