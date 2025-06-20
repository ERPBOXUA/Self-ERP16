from odoo import models, fields, api


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    linked_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Sale Order",
        domain="[('partner_id', '=', partner_id)]",
        related='st_line_id.linked_sale_order_id',
        depends=['st_line_id'],
    )
    linked_sale_order_visible = fields.Boolean(
        compute='_compute_linked_fields_visible',
    )

    linked_purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Linked Purchase Order",
        domain="[('partner_id', '=', partner_id)]",
        related='st_line_id.linked_purchase_order_id',
        depends=['st_line_id'],
    )
    linked_purchase_order_visible = fields.Boolean(
        compute='_compute_linked_fields_visible',
    )

    refund = fields.Boolean(
        string="Refund",
        related='st_line_id.refund',
        depends=['st_line_id'],
        readonly=False,
    )

    @api.depends('line_ids', 'refund')
    @api.onchange('line_ids', 'refund')
    def _compute_linked_fields_visible(self):
        for record in self:
            is_reconciled = record.st_line_id and record.st_line_id.is_reconciled or False
            st_line_amount = record.st_line_id and record.st_line_id.amount or 0.0
            balance_lines_receivable = record._get_opening_balance_lines('asset_receivable')
            balance_lines_payable = record._get_opening_balance_lines('liability_payable')
            record.linked_sale_order_visible = (
                (balance_lines_receivable or is_reconciled) and
                ((st_line_amount < 0.0 and record.refund) or (st_line_amount > 0.0 and not record.refund))
            )
            record.linked_purchase_order_visible = (
                (balance_lines_payable or is_reconciled) and
                ((st_line_amount > 0.0 and record.refund) or (st_line_amount < 0.0 and not record.refund))
            )

    @api.depends('linked_sale_order_id')
    @api.onchange('linked_sale_order_id')
    def _onchange_linked_sale_order_id(self):
        # Since 'bank.rec.widget' model is not "standard" and doesn't allow to save value
        # of 'linked_sale_order_id' via 'related' field, this hack is used to save changes of
        # 'linked_sale_order_id' directly into 'st_line_id'
        if self.st_line_id.linked_sale_order_id != self.linked_sale_order_id:
            self.st_line_id.linked_sale_order_id = self.linked_sale_order_id

            # populate contract from order (if defined)
            if self.linked_sale_order_id.contract_id and self.linked_sale_order_id.contract_id != self.contract_id:
                self.contract_id = self.linked_sale_order_id.contract_id

                # we must call it to write changes into statement line
                super()._onchange_contract_id()

    @api.onchange('linked_purchase_order_id')
    def _onchange_linked_purchase_order_id(self):
        # Since 'bank.rec.widget' model is not "standard" and doesn't allow to save value
        # of 'linked_purchase_order_id' via 'related' field, this hack is used to save changes of
        # 'linked_purchase_order_id' directly into 'st_line_id'
        if self.st_line_id.linked_purchase_order_id != self.linked_purchase_order_id:
            self.st_line_id.linked_purchase_order_id = self.linked_purchase_order_id

            # populate contract from order (if defined)
            if self.linked_purchase_order_id.contract_id and self.linked_purchase_order_id.contract_id != self.contract_id:
                self.contract_id = self.linked_purchase_order_id.contract_id

                # we must call it to write changes into statement line
                super()._onchange_contract_id()

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        super()._onchange_contract_id()

        if self.linked_sale_order_id and self.linked_sale_order_id.contract_id != self.contract_id:
            self.linked_sale_order_id = None

            # we must call it to write changes into statement line
            self._onchange_linked_sale_order_id()

        if self.linked_purchase_order_id and self.linked_purchase_order_id.contract_id != self.contract_id:
            self.linked_purchase_order_id = None

            # we must call it to write changes into statement line
            self._onchange_linked_purchase_order_id()

    @api.onchange('refund')
    def _onchange_refund(self):
        if self.st_line_id:
            # Hack (see comments for _onchange_linked_sale_order_id, _onchange_linked_purchase_order_id
            self.st_line_id.refund = self.refund
            # Update refund-dependent data
            account_receivable = self.partner_id.property_account_receivable_id
            account_payable = self.partner_id.property_account_payable_id
            manual_account = None
            open_balance_line = self._get_opening_balance_lines()
            if self.refund:
                if self.st_line_id.amount < 0.0 and account_receivable:
                    manual_account = account_receivable
                elif self.st_line_id.amount > 0.0 and account_payable:
                    manual_account = account_payable
            # TODO: test it with Anton to approve/reject this code changes
            #  For details see https://www.self-erp.com/web#id=575&menu_id=239&cids=1&action=343&active_id=39&model=project.task&view_type=form
            # else:
            #     if self.st_line_id.amount < 0.0 and account_payable:
            #         manual_account = account_payable
            #     elif self.st_line_id.amount > 0.0 and account_receivable:
            #         manual_account = account_receivable
            if manual_account:
                if self.form_account_id != manual_account:
                    self.form_account_id = manual_account
                for line in open_balance_line.filtered(lambda r: r.account_id != manual_account):
                    line.account_id = manual_account
            # Sync other data
            self._compute_linked_fields_visible()

    # TODO: test it with Anton to approve/reject this code changes
    # def _compute_line_ids(self):
    #     super()._compute_line_ids()
    #     for record in self:
    #         is_reconciled = record.st_line_id and record.st_line_id.is_reconciled or False
    #         if not is_reconciled and record.line_ids and record.form_account_id:
    #             open_balance_line = self._get_opening_balance_lines()
    #             for line in open_balance_line.filtered(lambda r: r.account_id != record.form_account_id):
    #                 line.account_id = record.form_account_id

    def _get_opening_balance_lines(self, account_type=None):
        return self.line_ids.filtered(
            lambda r: r.flag in ('auto_balance', 'new_aml', 'aml')
                      and r.partner_id
                      and r.account_id
                      and (not account_type or r.account_id.account_type == account_type)
        )
