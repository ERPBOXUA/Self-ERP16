from odoo import api, fields, models, tools, _

from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def compute_landed_cost(self):

        def _get_declaration(landed_cost):
            if len(landed_cost.picking_ids) == 1:
                return landed_cost.picking_ids
            else:
                raise UserError(_("Please specify only one stock picking to be able to use split method based on the data in the customs declaration (CCD)"))

        def _get_declaration_line(adjustement_line):
            cost = adjustement_line.cost_id
            declaration_line = _get_declaration(cost).move_ids.filtered(
                lambda line: line.product_id.id == adjustement_line.product_id.id
            )
            if len(declaration_line) == 1:
                return declaration_line
            else:
                raise UserError(_("Many or none declaration lines for product %s and cos %s") % (adjustement_line.product_id.name, cost.name))

        ret = super().compute_landed_cost()

        for cost in self:
            for line in cost.cost_lines:
                if line.split_method == 'by_custom_declaration':
                    declaration = _get_declaration(cost)
                    dec_line = declaration.customs_declaration_line_ids.filtered(
                        lambda rec: rec.product_id.id == line.product_id.id
                    )
                    if not dec_line or line.currency_id.compare_amounts(dec_line.amount, line.price_unit) != 0:
                        raise UserError(_("Wrong declaration line for product %s") % line.product_id.name)

        for cost in self:
            for adjustement_line in cost.valuation_adjustment_lines:
                if adjustement_line.cost_line_id.split_method == 'by_custom_declaration':
                    declaration_line = _get_declaration_line(adjustement_line)
                    if adjustement_line.cost_line_id.product_id == self.env.ref('selferp_l10n_ua_currency.product_product_expense_duty'):
                        adjustement_line.additional_landed_cost = declaration_line.customs_duty_amount
                    elif adjustement_line.cost_line_id.product_id == self.env.ref('selferp_l10n_ua_currency.product_product_expense_vat'):
                        adjustement_line.additional_landed_cost = declaration_line.vat_amount
                    elif adjustement_line.cost_line_id.product_id == self.env.ref('selferp_l10n_ua_currency.product_product_expense_customs_duty'):
                        adjustement_line.additional_landed_cost = declaration_line.customs_fee
                    elif adjustement_line.cost_line_id.product_id == self.env.ref('selferp_l10n_ua_currency.product_product_expense_excise_duty'):
                        adjustement_line.additional_landed_cost = declaration_line.excise_duty_amount
                    else:
                        raise UserError(_("The split method based on customs declaration data cannot be used for the following landed cost %s") % adjustement_line.product_id.display_name)
        return ret
