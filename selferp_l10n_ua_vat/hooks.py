from odoo import api, SUPERUSER_ID
from odoo.fields import Command


DEFAULT_UOM_CODES = {
    # Units
    'uom.product_uom_unit': '2009',
    'uom.product_uom_dozen': '2011',

    # WORKING TIME
    'uom.product_uom_day': '174',
    'uom.product_uom_hour': '175',

    # LENGTH
    'uom.product_uom_meter': '101',
    'uom.product_uom_millimeter': '105',
    'uom.product_uom_km': '102',
    'uom.product_uom_cm': '104',
    'uom.product_uom_inch': '116',
    'uom.product_uom_foot': '198',
    'uom.product_uom_yard': '117',
    'uom.product_uom_mile': '114',

    # SURFACE
    'uom.uom_square_meter': '123',
    'uom.uom_square_foot': '129',

    # VOLUME
    'uom.product_uom_litre': '138',
    'uom.product_uom_cubic_meter': '134',
    'uom.product_uom_floz': '156',
    'uom.product_uom_qt': '193',
    'uom.product_uom_gal': '150',
    'uom.product_uom_cubic_inch': '146',
    'uom.product_uom_cubic_foot': '147',

    # WEIGHT
    'uom.product_uom_kgm': '301',
    'uom.product_uom_gram': '303',
    'uom.product_uom_ton': '306',
    'uom.product_uom_lb': '318',
    'uom.product_uom_oz': '314',
}


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _install_default_uom_code(env)

#    _install_first_event(env)

    _set_vat_sequences(env)

    _change_tax_group_vat(env)

    _hide_sale_order_actions(env)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _show_sale_order_actions(env)


def _hide_sale_order_actions(env):
    # hide action for create invoice from a few sale orders
    action = env.ref('sale.action_view_sale_advance_payment_inv', raise_if_not_found=False)
    if action:
        action.write({
            'groups_id': [
                Command.clear(),
                Command.link(env.ref('base.group_no_one').id),
            ],
        })


def _show_sale_order_actions(env):
    # reset do default visibility of action
    # for create invoice from a few sale orders
    action = env.ref('sale.action_view_sale_advance_payment_inv', raise_if_not_found=False)
    if action:
        action.write({
            'groups_id': [Command.clear()],
        })


def _install_default_uom_code(env):
    """ Set code for predefined UoMs (once on module install)

        @see:
            https://buhgalter.com.ua/dovidnik/kspovo/klasifikator-sistemi-poznachen-odinits-vimiryuvannya-ta-obliku-dk-011-96/
    """
    for xml_id, umo_code in DEFAULT_UOM_CODES.items():
        uom = env.ref(xml_id, raise_if_not_found=False)
        if uom and not uom.code:
            uom.code = umo_code


def _install_first_event(env):
    id_361 = env.ref('l10n_ua.ua_psbp_361')# env['ir.model.data'].xmlid_to_res_id('l10n_ua.ua_psbp_361')
    account_361 = env['account.account'].browse(id_361)
    account_361.first_event = True


def _set_vat_sequences(env):
    companies = env['res.company'].search([])
    companies._setup_vat_sequences()


def _change_tax_group_vat(env):
    tax_group_vat_free = env.ref('l10n_ua.tax_group_vat20', raise_if_not_found=False)
    if tax_group_vat_free:
        tax_group_vat_free.write({'is_vat': True, 'vat_code': '20'})

    tax_group_vat_free = env.ref('l10n_ua.tax_group_vat14', raise_if_not_found=False)
    if tax_group_vat_free:
        tax_group_vat_free.write({'is_vat': True, 'vat_code': '14'})

    tax_group_vat_free = env.ref('l10n_ua.tax_group_vat7', raise_if_not_found=False)
    if tax_group_vat_free:
        tax_group_vat_free.write({'is_vat': True, 'vat_code': '7'})

    tax_group_vat_free = env.ref('l10n_ua.tax_group_vat_free', raise_if_not_found=False)
    if tax_group_vat_free:
        tax_group_vat_free.write({'is_vat': True, 'vat_code': '903'})
