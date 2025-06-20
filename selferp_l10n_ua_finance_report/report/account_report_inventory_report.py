from odoo import models, _


class AccountReportInventoryReportHandler(models.AbstractModel):
    _name = 'account.report.inventory.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Inventory Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['custom_columns_subheaders'] = [
            {'colspan': 1},
            {'name': _("Quantity"), 'colspan': 4},
            {'name': _("Balance"), 'colspan': 4},
        ]
