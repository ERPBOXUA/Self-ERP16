#
# This is a copy from module Web Actions View Reload by OCA for Odoo 15
# (https://apps.odoo.com/apps/modules/15.0/web_ir_actions_act_view_reload/).
#
# Should be removed (replaced with module dependency) on release module for Odoo 16.
#

from odoo import models


class IrActionsActViewReload(models.Model):
    _name = "ir.actions.act_view_reload"
    _inherit = "ir.actions.actions"
    _description = "View Reload"
