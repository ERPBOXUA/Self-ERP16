import logging

from odoo import fields, models


_logger = logging.getLogger(__name__)


class AccountBenefitCode(models.Model):
    _name = 'account.benefit_code'
    _description = "Benefits Guide"
    _order = 'code'
    _rec_names_search = ['code', 'name']
    _rec_name = 'code'

    code = fields.Char(
        string="Code",
        index=True,
        required=True,
    )
    name = fields.Text(
        string="Name",
        required=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    document_name = fields.Text(
        string="Document Name",
    )
    start_date = fields.Date(
        string="Start of the Benefit Code",
    )
    end_date = fields.Date(
        string="End of the Benefit Code",
    )
