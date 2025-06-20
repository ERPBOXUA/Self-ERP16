from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for rec_id in [
        'selferp_l10n_ua_currency.product_product_expense_customs_duty',
        'selferp_l10n_ua_currency.product_product_expense_duty',
        'selferp_l10n_ua_currency.product_product_expense_vat',
        'selferp_l10n_ua_currency.product_product_expense_excise_duty',
    ]:
        rec = env.ref(rec_id)
        rec.landed_cost_ok = True
        rec.split_method_landed_cost = 'by_custom_declaration'
