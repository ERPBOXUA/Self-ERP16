from odoo import models, fields, api


class ProductUKTZEDCode(models.Model):
    _name = 'product.uktzed_code'
    _description = "Code of the ukrainian classification of products for foreign economic activity"
    _order = 'sequence'
    _rec_names_search = ['name', 'code']

    name = fields.Char(
        string="Name",
        required=True,
    )

    full_name = fields.Char(
        string="Full Name",
        compute='_compute_full_name',
        store=True,
    )

    code = fields.Char(
        string="Code",
        index=True,
    )

    compact_code = fields.Char(
        string="Compact Code",
        compute='_compute_compact_code',
        store=True,
        index=True,
    )

    sequence = fields.Integer(
        string="Sequence",
        index=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    visible = fields.Boolean(
        string="Is Visible",
        default=False,
        index=True,
    )

    selectable = fields.Boolean(
        string="Is Selectable",
        default=False,
        index=True,
    )

    parent_id = fields.Many2one(
        comodel_name='product.uktzed_code',
        string="Parent",
        index=True,
        ondelete='cascade',
    )

    child_ids = fields.One2many(
        comodel_name='product.uktzed_code',
        inverse_name='parent_id',
        string="Children",
    )

    import_duty_rate_pref = fields.Char(
        string="Preferential import duty",
        help="Preferential import duty rate (%)",
    )

    import_duty_rate_full = fields.Char(
        string="Full import duty",
        help="Full import duty rate (%)",
    )

    import_duty_rate_special = fields.Char(
        string="Special import duty",
        help="Special import duty rate (%)",
    )

    additional_uom_name = fields.Char(
        string="Additional UoM",
    )

    @api.depends('name', 'parent_id')
    @api.onchange('name', 'parent_id')
    def _compute_full_name(self):
        for rec in self:
            full_name = rec.parent_id.full_name if rec.parent_id and rec.parent_id.visible else ''
            if rec.name:
                full_name += (full_name and ' ' or '') + (rec.name or '')
            rec.full_name = full_name

    @api.depends('code')
    @api.onchange('code')
    def _compute_compact_code(self):
        for rec in self:
            rec.compact_code = (rec.code or '').replace(' ', '')

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = record.code + ' ' + name
            res.append((record.id, name))
        return res
