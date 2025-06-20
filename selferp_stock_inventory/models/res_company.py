from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sequence_stock_inventory_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of Stock Inventory",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # create companies
        companies = super().create(vals_list)

        # setup sequences
        companies._setup_stock_inventory_sequences()

        return companies

    def unlink(self):
        # remove sequences
        self.mapped('sequence_stock_inventory_id').unlink()

        # remove companies
        return super().unlink()

    def _setup_stock_inventory_sequences(self):
        without_sequence = self.filtered(lambda r: not r['sequence_stock_inventory_id'])
        sequence = self.env.ref('selferp_stock_inventory.seq_stock_inventory', raise_if_not_found=False)

        if not without_sequence or not sequence:
            return

        for record in without_sequence:
            record['sequence_stock_inventory_id'] = sequence.copy(
                {
                    'company_id': record.id,
                }
            )
