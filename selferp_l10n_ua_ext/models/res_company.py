import base64

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_legal_form = fields.Selection(
        selection=[
            ('legal', "Legal entity"),
            ('private', "Private entrepreneur"),
        ],
        required=True,
        default='legal',
        string="Company legal form",
    )

    general_bank_account_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Main bank account",
        domain="[('partner_id', '=', partner_id)]",
        check_company=True,
        help="Bank Account Number to which the invoice will be paid. "
        "A Company bank account if this is a Customer Invoice or Vendor Credit Note, "
        "otherwise a Partner bank account number.",
    )

    director_id = fields.Many2one(
        comodel_name='res.partner',
        string="Director",
    )
    chief_accountant_id = fields.Many2one(
        comodel_name='res.partner',
        string="Chief Accountant",
    )

    code_kved = fields.Char(
        string="KVED",
    )

    code_kotauu = fields.Char(
        string="KOTAUU",
    )

    code_kprv = fields.Char(
        string="KPRV",
    )

    tax_inspection_id = fields.Many2one(
        comodel_name='account.tax.inspection',
        ondelete='restrict',
        string="Tax Inspection",
    )

    def get_director_name(self):
        self.ensure_one()
        return self.director_id and self.director_id.name or None

    def get_director_vat(self):
        self.ensure_one()
        return self.director_id and self.director_id.vat or None

    def get_chief_accountant_name(self):
        self.ensure_one()
        return self.chief_accountant_id and self.chief_accountant_id.name or None

    def get_chief_accountant_vat(self):
        self.ensure_one()
        return self.chief_accountant_id and self.chief_accountant_id.vat or None

    def _get_asset_style_b64(self):
        # One bundle for everyone, so this method
        # necessarily updates the style for every company at once
        if self.external_report_layout_id.key == 'selferp_l10n_ua_ext.report_layout_template_light_custom':
            company_ids = self.sudo().search([])
            company_styles = self.env['ir.qweb']._render(
                'selferp_l10n_ua_ext.report_layout_template_light_custom_styles',
                {
                    'company_ids': company_ids,
                },
                raise_if_not_found=False,
            )
            return base64.b64encode(company_styles.encode())

        else:
            return super()._get_asset_style_b64()
