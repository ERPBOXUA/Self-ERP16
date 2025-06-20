from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        return super()._get_translation_frontend_modules_name() + ['selferp_l10n_ua_salary']
