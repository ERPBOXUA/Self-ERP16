from odoo import models

from odoo.addons.selferp_l10n_ua_salary.utils.hr_salary_rule_utils import get_rbo_structures, get_rbo_structures_data


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        result = super()._load(company)
        if company:
            self._setup_salary_rules_accounts(company)
        return result

    def _setup_salary_rules_accounts(self, company):
        if company:
            structures = get_rbo_structures(self.env)
            if structures:
                struct_type_clc = self.env.ref('selferp_l10n_ua_salary.hr_payroll_structure_type_civil_law_contract', False)
                for structure in structures:
                    structure_data = get_rbo_structures_data(self.env, structure.type_id == struct_type_clc and '102' or '101')
                    rules = {(rule.code, rule.category_id.id): rule for rule in structure.rule_ids}
                    for rule_key, rule_values in structure_data.items():
                        rule = rules.get(rule_key)
                        if rule:
                            account_debit_code = rule_values.get('account_debit_code')
                            account_credit_code = rule_values.get('account_credit_code')
                            if account_debit_code or account_credit_code:
                                rule = rule.with_context(force_rules_companies=company)
                                if account_debit_code:
                                    rule.account_debit_code = account_debit_code
                                if account_credit_code:
                                    rule.account_credit_code = account_credit_code
