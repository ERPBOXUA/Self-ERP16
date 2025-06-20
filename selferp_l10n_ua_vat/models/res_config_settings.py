from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vat_payer = fields.Boolean(
        related='company_id.vat_payer',
        readonly=False,
    )

    vat_account_id = fields.Many2one(
        related='company_id.vat_account_id',
        readonly=False,
    )
    vat_account_unconfirmed_id = fields.Many2one(
        related='company_id.vat_account_unconfirmed_id',
        readonly=False,
    )
    vat_account_confirmed_id = fields.Many2one(
        related='company_id.vat_account_confirmed_id',
        readonly=False,
    )
    vat_account_unconfirmed_credit_id = fields.Many2one(
        related='company_id.vat_account_unconfirmed_credit_id',
        readonly=False,
    )
    vat_account_confirmed_credit_id = fields.Many2one(
        related='company_id.vat_account_confirmed_credit_id',
        readonly=False,
    )

    vat_journal_id = fields.Many2one(
        related='company_id.vat_journal_id',
        readonly=False,
    )
    vendor_vat_journal_id = fields.Many2one(
        related='company_id.vendor_vat_journal_id',
        readonly=False,
    )

    first_event_journal_id = fields.Many2one(
        related='company_id.first_event_journal_id',
        readonly=False,
    )

    vat_default_tax_id = fields.Many2one(
        related='company_id.vat_default_tax_id',
        readonly=False,
    )
    vat_default_tax_credit_id = fields.Many2one(
        related='company_id.vat_default_tax_credit_id',
        readonly=False,
    )

    vat_default_product_id = fields.Many2one(
        related='company_id.vat_default_product_id',
        readonly=False,
    )

    vat_reg_terms_1 = fields.Integer(
        related='company_id.vat_reg_terms_1',
        readonly=False,
    )
    vat_reg_terms_1_next_month = fields.Boolean(
        related='company_id.vat_reg_terms_1_next_month',
        readonly=False,
    )
    vat_reg_terms_2 = fields.Integer(
        related='company_id.vat_reg_terms_2',
        readonly=False,
    )
    vat_reg_terms_2_next_month = fields.Boolean(
        related='company_id.vat_reg_terms_2_next_month',
        readonly=False,
    )

    @api.onchange('vat_payer')
    def _onchange_vat_payer(self):
        def _find_journal(company, id_journal, code_journal, name_journal):
            xml_id = f'selferp_l10n_ua_vat.{company.id}_{id_journal}'
            journal = self.env.ref(xml_id, raise_if_not_found=False)
            if not journal:
                journal = self.env['account.journal'].search([('code', '=', code_journal)], limit=1)
            if not journal:
                journal = self.env['account.journal'].create(
                    {
                        'name': name_journal,
                        'type': 'general',
                        'code': code_journal,
                        'company_id': company.id,
                    }
                )
                self.env['ir.model.data']._update_xmlids(
                    [
                        {
                            'xml_id': xml_id,
                            'record': journal,
                            'noupdate': True,
                        }
                    ]
                )

            return journal

        for record in self:
            if record.vat_payer:
                (
                    vat_account,
                    vat_account_unconfirmed,
                    vat_account_confirmed,
                    vat_account_unconfirmed_credit,
                    vat_account_confirmed_credit,
                ) = record.company_id.get_vat_default_accounts()

                vat_default_tax, vat_default_tax_credit = record.company_id.get_vat_default_taxes()

                values = {}
                if not record.vat_account_id and vat_account:
                    values['vat_account_id'] = vat_account.id
                if not record.vat_account_unconfirmed_id and vat_account_unconfirmed:
                    values['vat_account_unconfirmed_id'] = vat_account_unconfirmed.id
                if not record.vat_account_confirmed_id and vat_account_confirmed:
                    values['vat_account_confirmed_id'] = vat_account_confirmed.id
                if not record.vat_account_unconfirmed_credit_id and vat_account_unconfirmed_credit:
                    values['vat_account_unconfirmed_credit_id'] = vat_account_unconfirmed_credit.id
                if not record.vat_account_confirmed_credit_id and vat_account_confirmed_credit:
                    values['vat_account_confirmed_credit_id'] = vat_account_confirmed_credit.id
                if not record.vat_default_tax_id and vat_default_tax:
                    values['vat_default_tax_id'] = vat_default_tax.id
                if not record.vat_default_tax_credit_id and vat_default_tax_credit:
                    values['vat_default_tax_credit_id'] = vat_default_tax_credit.id

                if not record.vat_default_product_id:
                    vat_default_product = self.env.ref('selferp_l10n_ua_vat.product_product_vat_default', raise_if_not_found=False)
                    if vat_default_product:
                        values['vat_default_product_id'] = vat_default_product.id

                if not record.vat_journal_id:
                    values['vat_journal_id'] = _find_journal(
                        record.company_id,
                        'vat_journal',
                        "ПЗ",
                        "Податкові забов'язання",
                    ).id

                if not record.vendor_vat_journal_id:
                    values['vendor_vat_journal_id'] = _find_journal(
                        record.company_id,
                        'vendor_vat_journal',
                        "ПК",
                        "Податковий кредит",
                    ).id

                if not record.first_event_journal_id:
                    values['first_event_journal_id'] = _find_journal(
                        record.company_id,
                        'first_event_journal',
                        "ПП",
                        "Перша подія",
                    ).id

                if values:
                    record.update(values)

            else:
                record.update(
                    {
                        'vat_account_id': None,
                        'vat_account_unconfirmed_id': None,
                        'vat_account_confirmed_id': None,
                        'vat_account_unconfirmed_credit_id': None,
                        'vat_account_confirmed_credit_id': None,
                        'vat_default_tax_id': None,
                        'vat_default_tax_credit_id': None,
                    }
                )
