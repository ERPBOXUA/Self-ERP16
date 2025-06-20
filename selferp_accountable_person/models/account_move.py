from textwrap import shorten

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_advance_report = fields.Boolean(
        string="Advance Report",
        default=False,
    )

    can_convert_to_advance_report = fields.Boolean(
        compute='_compute_convert_buttons_visibility',
    )
    can_convert_to_vendor_bill = fields.Boolean(
        compute='_compute_convert_buttons_visibility',
    )

    @api.depends(
        'state',
        'move_type',
        'is_advance_report',
        'partner_id',
        'partner_id.is_company',
        'partner_id.property_account_accountable_id',
        'partner_id.property_account_accountable_id.account_type',
    )
    @api.onchange('state', 'move_type', 'is_advance_report', 'partner_id')
    def _compute_convert_buttons_visibility(self):
        for rec in self:
            rec.can_convert_to_advance_report = (
                rec.id
                and rec.state == 'draft'
                and rec.move_type == 'in_invoice'
                and not rec.is_advance_report
                and rec.partner_id
                and not rec.partner_id.is_company
                and rec.partner_id.property_account_accountable_id
                and rec.partner_id.property_account_accountable_id.account_type == 'liability_payable'
            )
            rec.can_convert_to_vendor_bill = (
                rec.id
                and rec.state == 'draft'
                and rec.move_type == 'in_invoice'
                and rec.is_advance_report
                and rec.partner_id
            )

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if self.is_advance_report and self.partner_id and not self.partner_id.property_account_accountable_id:
            raise UserError(_("There is no accountable account is set for vendor '%s'") % self.partner_id.name)
        return super()._onchange_partner_id()

    def action_convert_to_vendor_bill(self):
        self.ensure_one()
        if self.can_convert_to_vendor_bill:
            self.is_advance_report = False

    def action_convert_to_advance_report(self):
        self.ensure_one()
        if self.can_convert_to_advance_report:
            self.is_advance_report = True

    def action_convert_to_vendor_bill_multy(self):
        for rec in self.filtered(lambda r: r.can_convert_to_vendor_bill):
            rec.action_convert_to_vendor_bill()

    def action_convert_to_advance_report_multy(self):
        if self:
            convertable = self.filtered(lambda r: r.can_convert_to_advance_report)
            if len(convertable) == len(self):
                for rec in self:
                    rec.action_convert_to_advance_report()
            elif len(convertable) == 0:
                raise UserError(_("No one of the provided Vendor Bills can be converted to an Advance Report."))
            else:
                context = dict(self.env.context)
                context.pop('active_ids', False)
                context['create'] = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'sticky': False,
                        'title': _("Warning!"),
                        'message': _("Some Vendor Bills can not be converted to Advance Reports."),
                        'next': {
                            'name': _("Can not convert to an Advance Report"),
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.move',
                            'context': context,
                            'domain': [('id', 'in', (self - convertable).ids)],
                            'view_mode': 'list',
                            'views': [[False, 'list'], [False, 'form']],
                        },
                    },
                }

    def _get_move_display_name(self, show_ref=False):
        if self.move_type == 'in_invoice' and self.is_advance_report:
            name = ''
            if self.state == 'draft':
                name = _("Draft Advance Report")
                name += ' '
            if not self.name or self.name == '/':
                name += '(* %s)' % str(self.id)
            else:
                name += self.name
                if self.env.context.get('input_full_display_name'):
                    if self.partner_id:
                        name += f', {self.partner_id.name}'
                    if self.date:
                        name += f', {format_date(self.env, self.date)}'
            return name + (f' ({shorten(self.ref, width=50)})' if show_ref and self.ref else '')

        return super()._get_move_display_name(show_ref=show_ref)
