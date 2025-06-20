import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class ProductDKPPCode(models.Model):
    _name = 'product.dkpp_code'
    _description = "Code for Ukrainian State classifier of products and services"
    _order = 'code'
    _rec_names_search = ['name', 'code']

    name = fields.Char(
        string="Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        index=True,
        required=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    selectable = fields.Boolean(
        string="Is Selectable",
        index=True,
        default=False,
    )
    parent_id = fields.Many2one(
        comodel_name='product.dkpp_code',
        ondelete='cascade',
        index=True,
        string="Parent",
    )
    child_ids = fields.One2many(
        comodel_name='product.dkpp_code',
        inverse_name='parent_id',
        string="Children",
    )
    uktzed = fields.Char(
        string="UKTZED",
    )
    full_code = fields.Char(
        string="Full Code",
        compute='_compute_full_code',
        store=True,
        recursive=True,
    )

    @api.depends('code', 'parent_id')
    def _compute_full_code(self):
        for rec in self:
            rec.full_code = (rec.parent_id.full_code if rec.parent_id else '/') + (rec.code or '') + '/'

    def name_get(self):
        return [(rec.id, f'{rec.code} {rec.name}') for rec in self]
