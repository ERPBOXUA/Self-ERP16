from odoo import api, models, _
from odoo.osv import expression


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _init_options_account_type(self, options, previous_options=None):
        super()._init_options_account_type(options, previous_options=previous_options)

        # add custom per report
        if self.filter_account_type and self == self.env.ref('account_reports.partner_ledger_report'):
            # check already selected
            employee_selected = any(map(
                lambda r: r['id'] == 'employee' and r.get('selected'),
                previous_options and previous_options.get('account_type') or [],
            ))

            # add option
            options['account_type'].append({
                'id': 'employee',
                'name': _("Employee"),
                'selected': employee_selected,
            })

            # change title
            if employee_selected:
                if any(map(
                    lambda r: r['id'] != 'employee' and r.get('selected'),
                    previous_options and previous_options.get('account_type') or [],
                )):
                    options['account_display_name'] = _("Partners")
                else:
                    options['account_display_name'] = _("Employees")

    @api.model
    def _get_options_account_type_domain(self, options):
        # check custom domain per report
        if self.filter_account_type and self == self.env.ref('account_reports.partner_ledger_report'):
            if not options.get('account_type') or len(options.get('account_type')) == 0:
                return []

            # get list of employees
            employee_ids = [
                r['address_home_id'][0]
                for r in self.env['hr.employee'].search_read(
                    domain=[('address_home_id', '!=', False)],
                    fields=['address_home_id'],
                )
            ]

            # collect domain by selected account types
            all_domains = []
            selected_domains = []

            for opt in options.get('account_type', []):
                if opt['id'] == 'trade_receivable':
                    domain = [
                        ('account_id.non_trade', '=', False),
                        ('account_id.account_type', '=', 'asset_receivable'),
                    ]
                elif opt['id'] == 'non_trade_receivable':
                    domain = [
                        ('account_id.non_trade', '=', True),
                        ('account_id.account_type', '=', 'asset_receivable'),
                    ]
                elif opt['id'] == 'trade_payable':
                    domain = [
                        ('account_id.non_trade', '=', False),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('partner_id', 'not in', employee_ids),                 # not include employees
                    ]
                elif opt['id'] == 'non_trade_payable':
                    domain = [
                        ('account_id.non_trade', '=', True),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('partner_id', 'not in', employee_ids),                 # not include employees
                    ]
                elif opt['id'] == 'employee':
                    domain = [
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('partner_id', 'in', employee_ids),                     # include employees only
                    ]

                if opt['selected']:
                    selected_domains.append(domain)
                all_domains.append(domain)

            # join selected domains (or all if no any selected)
            accounts_domain = expression.OR(selected_domains or all_domains)

            # return complete domain
            return accounts_domain

        else:
            # get super domain
            return super()._get_options_account_type_domain(options)
