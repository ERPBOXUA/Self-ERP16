#
# This is a copy from module Web Actions Multi by OCA for Odoo 15
# (https://apps.odoo.com/apps/modules/15.0/web_ir_actions_act_multi/).
#
# Should be removed (replaced with module dependency) on release module for Odoo 16.
#

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrActionsActMulti(models.Model):
    _name = "ir.actions.act_multi"
    _description = "Action Mulit"
    _inherit = "ir.actions.actions"
    # _table = "ir_actions"

    type = fields.Char(default="ir.actions.act_multi")

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {"actions"}
