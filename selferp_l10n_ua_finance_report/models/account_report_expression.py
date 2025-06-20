from odoo import models, _, api
from odoo.exceptions import UserError

from .account_report import CUSTOM_ENGINE_GROUPED_BY_PARTNER_REGEX


class AccountReportExpression(models.Model):
    _inherit = 'account.report.expression'

    @api.constrains('subformula')
    def _check_subformula(self):
        for record in self:
            if (
                record.engine == 'custom'
                and record.formula == '_report_custom_engine_grouped_by_partner'
                and not CUSTOM_ENGINE_GROUPED_BY_PARTNER_REGEX.match(record.subformula)
            ):
                raise UserError(_(
                    "Invalid subformula '%s' for _report_custom_engine_grouped_by_partner in %s",
                    record.subformula,
                    record.display_name,
                ))
