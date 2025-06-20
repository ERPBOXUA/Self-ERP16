from odoo import fields, models, api


class HrOrderType(models.Model):
    _name = 'hr.order.type'
    _description = "Type of order"
    _order = 'name'

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    type_group_id = fields.Many2one(
        comodel_name='hr.order.type.group',
        required=True,
        string="Order Type Group"
    )
