from num2words import num2words

from odoo import models, tools


class Currency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text(self, amount):
        self.ensure_one()
        lang = tools.get_lang(self.env)

        if lang.iso_code == 'uk':
            if amount:
                return num2words(
                    tools.float_utils.float_round(float(amount), precision_digits=self.decimal_places),
                    lang=lang.iso_code,
                    to='currency',
                    cents=True,
                    currency=self.name,
                )
            else:
                return ''

        else:
            return super().amount_to_text(amount)
