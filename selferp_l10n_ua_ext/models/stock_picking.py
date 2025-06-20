from odoo import api, models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    accounting_date = fields.Datetime(
        string="Accounting Date",
    )

    def _action_done(self):
        if any(self.mapped('accounting_date')):
            for record in self:
                if record.accounting_date:
                    record = record.with_context(force_period_date=record.accounting_date)

                super(StockPicking, record)._action_done()

            return True

        else:
            return super()._action_done()
