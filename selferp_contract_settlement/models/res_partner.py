from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    contract_count = fields.Integer(
        compute='_compute_contract_count',
    )

    contract_ids = fields.One2many(
        comodel_name='account.contract',
        inverse_name='partner_id',
    )

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = len(rec.contract_ids)

    def action_view_contract(self):
        self.ensure_one()

        action = self.env['ir.actions.actions']._for_xml_id('selferp_contract_settlement.account_contract_action')

        contracts = self.contract_ids
        if len(contracts) > 1:
            action['domain'] = [('partner_id', '=', self.id)]
        else:
            action.update({
                'res_id': contracts.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })

        return action

