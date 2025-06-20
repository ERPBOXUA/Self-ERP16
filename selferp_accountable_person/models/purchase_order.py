from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import format_amount


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_advance_report = fields.Boolean(
        string="Advance Report",
        default=False,
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.is_advance_report and self.partner_id and not self.partner_id.property_account_accountable_id:
            raise UserError(_("There is no accountable account is set for vendor '%s'") % self.partner_id.name)

    def _prepare_invoice(self):
        result = super()._prepare_invoice()
        if result:
            result['is_advance_report'] = self.is_advance_report
        return result

    def action_create_invoice(self):
        for order in self:
            if order.is_advance_report:
                account_accountable = order.partner_id and order.partner_id.property_account_accountable_id or None
                if not account_accountable:
                    raise UserError(_("You must first set the vendor's account accountable for %s!") % order.partner_id.name)
        return super().action_create_invoice()

    @api.model
    def retrieve_dashboard(self):
        self.check_access_rights('read')

        result = {
            'all_to_send': 0,
            'all_waiting': 0,
            'all_late': 0,
            'my_to_send': 0,
            'my_waiting': 0,
            'my_late': 0,
            'all_avg_order_value': 0,
            'all_avg_days_to_purchase': 0,
            'all_total_last_7_days': 0,
            'all_sent_rfqs': 0,
            'company_currency_symbol': self.env.company.currency_id.symbol,
        }

        one_week_ago = fields.Datetime.to_string(fields.Datetime.now() - relativedelta(days=7))

        query = """
            SELECT 
                COUNT(1)
            FROM 
                mail_message m
                JOIN purchase_order po ON (po.id = m.res_id)
            WHERE 
                m.create_date >= %s
                AND m.model = 'purchase.order'
                AND m.message_type = 'notification'
                AND m.subtype_id = %s
                AND po.company_id = %s
                AND po.is_advance_report = FALSE;
        """

        self.env.cr.execute(query, (one_week_ago, self.env.ref('purchase.mt_rfq_sent').id, self.env.company.id,))
        res = self.env.cr.fetchone()
        result['all_sent_rfqs'] = res[0] or 0

        # easy counts
        result['all_to_send'] = self.search_count([
            ('state', '=', 'draft'),
            ('is_advance_report', '=', False),
        ])
        result['my_to_send'] = self.search_count([
            ('state', '=', 'draft'),
            ('user_id', '=', self.env.uid),
            ('is_advance_report', '=', False),
        ])
        result['all_waiting'] = self.search_count([
            ('state', '=', 'sent'),
            ('date_order', '>=', fields.Datetime.now()),
            ('is_advance_report', '=', False),
        ])
        result['my_waiting'] = self.search_count([
            ('state', '=', 'sent'),
            ('date_order', '>=', fields.Datetime.now()),
            ('user_id', '=', self.env.uid),
            ('is_advance_report', '=', False),
        ])
        result['all_late'] = self.search_count([
            ('state', 'in', ['draft', 'sent', 'to approve']),
            ('date_order', '<', fields.Datetime.now()),
            ('is_advance_report', '=', False),
        ])
        result['my_late'] = self.search_count([
            ('state', 'in', ['draft', 'sent', 'to approve']),
            ('date_order', '<', fields.Datetime.now()),
            ('user_id', '=', self.env.uid),
            ('is_advance_report', '=', False),
        ])

        query = """
            SELECT 
                AVG(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)),
                AVG(extract(epoch from age(po.date_approve,po.create_date)/(24*60*60)::decimal(16,2))),
                SUM(CASE WHEN po.date_approve >= %s THEN COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total) ELSE 0 END)
            FROM 
                purchase_order po
            WHERE 
                po.state in ('purchase', 'done')
                AND po.company_id = %s
                AND po.is_advance_report = FALSE
        """
        self._cr.execute(query, (one_week_ago, self.env.company.id,))
        res = self.env.cr.fetchone()

        result['all_avg_days_to_purchase'] = round(res[1] or 0, 2)
        currency = self.env.company.currency_id
        result['all_avg_order_value'] = format_amount(self.env, res[0] or 0, currency)
        result['all_total_last_7_days'] = format_amount(self.env, res[2] or 0, currency)

        return result
