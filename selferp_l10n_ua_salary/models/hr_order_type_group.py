from odoo import fields, models, api


class HrOrderTypeGroup(models.Model):
    _name = 'hr.order.type.group'
    _description = "Group of order types"
    _order = 'name'

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    letter = fields.Char(
        string="Letter",
        required=True,
    )

    property_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence",
        check_company=True,
        company_dependent=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        order_type_groups = super().create(vals_list)

        return self.create_sequences_for_all_type_groups(order_type_groups)

    def create_order_type_group_sequence(self, company_id):
        self.ensure_one()

        seq = self.env['ir.sequence'].create({
            'name': 'Order type group sequence - %s (%s)' % (self.letter, self.name),
            'code': 'hr.order.type.group-%s_%s' % (self.id, company_id),
            'prefix': '№ ',
            'suffix': '-' + self.letter,
            'padding': 0,
            'company_id': company_id,
            'implementation': 'no_gap',
        })

        return seq or None

    @api.model
    def create_sequences_for_all_type_groups(self, order_type_groups):
        for order_type_group in order_type_groups.sudo():
            for company in self.env['res.company'].sudo().with_context(active_test=False).search([]):
                order_type_group.with_company(company).property_sequence_id = order_type_group.create_order_type_group_sequence(company.id)
        return order_type_groups
