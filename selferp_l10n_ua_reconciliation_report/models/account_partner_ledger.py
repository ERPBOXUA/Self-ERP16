import json

from odoo import models, fields, _


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def action_export_file_reconciliation_report(self, options, params):
        report = self.env.ref('account_reports.partner_ledger_report')

        options = self._get_options_for_reconciliation_report(report, options)

        return {
            'type': 'ir_actions_reconciliation_report_download',
            'data': {
                'options': json.dumps(options),
                'file_generator': 'export_reconciliation_report_to_xml',
            }
        }

    def export_reconciliation_report_to_xml(self, options):
        base_url = self.get_base_url()

        context = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        report = self.env.ref('account_reports.partner_ledger_report')

        print_mode_self = report.with_context(print_mode=True)

        lines = print_mode_self._get_lines(options)

        body_html = print_mode_self.get_html(
            options,
            self._upgrade_lines_for_reconciliation_report(lines),
            template='selferp_l10n_ua_reconciliation_report.reconciliation_report_body_template'
        )

        body = self.env['ir.ui.view']._render_template(
            'selferp_l10n_ua_reconciliation_report.reconciliation_report_template',
            values=dict(context, body_html=body_html),
        )

        bodies, html_ids, header, footer, specific_paperformat_args = self.env['ir.actions.report']._prepare_html(body, report_model=False)

        file_content = self.env['ir.actions.report']._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=False,
        )

        return {
            'file_name': print_mode_self.get_default_report_filename('pdf'),
            'file_content': file_content,
            'file_type': 'pdf',
        }

    def _upgrade_lines_for_reconciliation_report(self, lines):
        for line in lines:
            line_id = line.get('id')
            record_type = ''

            if 'initial' in line_id:
                initial_balance = line.get('columns')[-1]['no_format']

                if initial_balance < 0:
                    line['company_debit'] = 0
                    line['company_credit'] = initial_balance * -1
                    line['partner_debit'] = initial_balance * -1
                    line['partner_credit'] = 0
                else:
                    line['company_debit'] = initial_balance
                    line['company_credit'] = 0
                    line['partner_debit'] = 0
                    line['partner_credit'] = initial_balance

            elif 'account.move.line' in line_id:
                company_debit = line.get('columns')[5]['no_format']
                company_credit = line.get('columns')[6]['no_format']
                line['document'] = line.get('columns')[2]['name']

                if company_debit < 0 or company_credit < 0:
                    line['company_debit'] = company_credit * -1
                    line['company_credit'] = company_debit * -1
                    line['partner_debit'] = company_debit * -1
                    line['partner_credit'] = company_credit * -1
                else:
                    line['company_debit'] = company_debit
                    line['company_credit'] = company_credit
                    line['partner_debit'] = company_credit
                    line['partner_credit'] = company_debit

                account_move_line_id = self.env['account.report']._get_model_info_from_id(line.get('id'))[1]
                account_move_line = self.env['account.move.line'].browse(account_move_line_id).exists()
                if account_move_line:
                    account_move_type = account_move_line.move_id.move_type
                    journal_type = account_move_line.journal_id.type
                    if journal_type and account_move_type:
                        if journal_type == 'bank' or journal_type == 'cash':
                            record_type = 'оплата'

                        elif journal_type == 'sale':
                            if account_move_type == 'out_invoice':
                                record_type = 'реалізація'
                            elif account_move_type == 'out_refund':
                                record_type = 'повернення'

                        elif journal_type == 'purchase':
                            if account_move_type == 'in_invoice':
                                record_type = 'купівля'
                            elif account_move_type == 'in_refund':
                                record_type = 'повернення'

            line['record_type'] = record_type

        return lines

    def _get_options_for_reconciliation_report(self, report, options):
        self._custom_options_initializer(report, options)

        if not options['selected_partner_ids']:
            partner_id = self.env['account.report']._get_model_info_from_id(self.env.context['active_id'])[1]

            if partner_id:
                options['partner_ids'].append(partner_id)

            selected_partner = self.env['res.partner'].browse(partner_id).exists()

            if selected_partner:
                options['selected_partner_ids'].append(selected_partner.display_name)

        options['company_name'] = self.env.company.name
        options['date_from_converted'] = fields.Date.from_string(options['date']['date_from']).strftime('%d.%m.%Y')
        options['date_to_converted'] = fields.Date.from_string(options['date']['date_to']).strftime('%d.%m.%Y')

        # switch off group by contracts
        options['groupby_contract'] = False

        return options
