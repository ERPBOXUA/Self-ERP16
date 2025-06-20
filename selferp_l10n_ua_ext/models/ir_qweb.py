from babel import dates, numbers
from num2words import num2words

from odoo import models
from odoo.tools.safe_eval import wrap_module


class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _prepare_environment(self, values):
        IrQweb = super()._prepare_environment(values)

        babel_dates = wrap_module(dates, [
            'format_date',
        ])
        babel_numbers = wrap_module(numbers, [
            'format_currency',
        ])

        values.update(
             num2words=num2words,
             babel_dates=babel_dates,
             babel_numbers=babel_numbers,
        )

        return IrQweb
