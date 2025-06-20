from odoo import api, fields, models


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    is_vat = fields.Boolean(
        string="VAT",
        default=False,
        index=True,
        help="Check the box if the selected tax is VAT tax",
    )
    vat_code = fields.Char(
        string="VAT Code",
        index=True,
        copy=False,
        help="The value of the tax code of invoices/adjustments for the export in XML purpose",
    )

    @api.onchange('is_vat')
    def _onchange_is_vat(self):
        for record in self:
            if not record.is_vat:
                record.vat_code = None
