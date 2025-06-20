from odoo import models, _
from odoo.tools import format_date


class AssetReportCustomHandler(models.AbstractModel):
    _inherit = 'account.asset.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # del acquisition_date
        options['columns'] = list(filter(lambda c: c['expression_label'] != 'acquisition_date', options['columns']))

        # Fix characteristics' count columns; added commissioning_date, asset_number, original_value
        options['custom_columns_subheaders'][0]['colspan'] = 7

    def _query_lines(self, options, prefix_to_match=None, forced_account_id=None):
        lines = super()._query_lines(options, prefix_to_match, forced_account_id)

        asset_add_vals = self._query_additional_values(lines)

        for line in lines:
            recs = list(filter(lambda r: (r['asset_id'], r['account_id']) == (line[1], line[0]), asset_add_vals))
            if recs:
                add_vals = recs[0]
                cur_line = line[2]

                if add_vals['asset_method_number'] and add_vals['asset_method'] in ('100', '50/50'):  # some assets might have 0 depreciations because they dont lose value
                    total_months = int(add_vals['asset_method_number']) * int(add_vals['asset_method_period'])
                    months = total_months % 12
                    years = total_months // 12
                    asset_depreciation_rate = ' '.join(
                        part
                        for part in [
                            years and _("%s y", years),
                            months and _("%s m", months),
                        ]
                        if part
                    )
                elif add_vals['asset_method'] in ('100', '50/50'):
                    asset_depreciation_rate = '0.00 %'
                else:
                    asset_depreciation_rate = cur_line['duration_rate']

                method = (
                    (add_vals['asset_method'] == '100' and '100%')
                    or (add_vals['asset_method'] == '50/50' and '50/50')
                    or cur_line['method']
                )

                vals = {
                    'acquisition_date_ua': cur_line['acquisition_date'],
                    'commissioning_date': add_vals['commissioning_date'] and format_date(self.env, add_vals['commissioning_date']) or '',
                    'asset_number': add_vals['asset_number'],
                    'asset_original_value': add_vals['asset_original_value'],
                    'method': method,
                    'duration_rate': asset_depreciation_rate,
                }
            else:
                vals = {
                    'acquisition_date_ua': cur_line['acquisition_date'],
                    'commissioning_date': '',
                    'asset_number': None,
                    'asset_original_value': None,
                }

            line[2].update(vals)

        return lines

    def _query_additional_values(self, lines):
        if not lines:
            return []

        query_params = {'asset_account_ids': tuple((r[1], r[0]) for r in lines)}

        sql = f'''
            SELECT asset.id AS asset_id,
                   asset.account_asset_id AS account_id,
                   asset.original_value AS asset_original_value,
                   asset.commissioning_date AS commissioning_date,
                   asset.asset_number AS asset_number,
                   asset.method AS asset_method,
                   asset.method_number AS asset_method_number,
                   asset.method_period AS asset_method_period
              FROM account_asset AS asset
             WHERE (asset.id, asset.account_asset_id) in %(asset_account_ids)s
          ORDER BY asset.id, asset.account_asset_id;
        '''
        self._cr.execute(sql, query_params)
        results = self._cr.dictfetchall()

        return results
