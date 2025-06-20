from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    accounts_accountable = env['account.account'].search([('code', 'in', ('372100', '372200'))])
    if accounts_accountable:
        accounts_accountable.write({'account_type': 'liability_payable'})

    Account = env['account.account']
    partners = env['res.partner'].search([('property_account_accountable_id', '=', False), ('is_company', '=', False)])
    for partner in partners:
        company_id = partner.company_id and partner.company_id.id or env.company.id
        account = Account.search([('code', '=', '372100'), ('company_id', '=', company_id)])
        if not account:
            account = Account.search([('code', '=', '372100'), ('company_id', '=', False)])
        if account:
            partner.property_account_accountable_id = account

    account_action = env.ref('account.action_move_in_invoice_type', raise_if_not_found=False)
    if account_action:
        account_action.write({
            'domain': "[('move_type', '=', 'in_invoice'), ('is_advance_report', '=', False)]",
            'context': "{'default_move_type': 'in_invoice', 'default_is_advance_report': False}",
        })

    purchase_rfq_action = env.ref('purchase.purchase_rfq', raise_if_not_found=False)
    if purchase_rfq_action:
        purchase_rfq_action.domain = "[('is_advance_report', '=', False)]"

    purchase_form_action = env.ref('purchase.purchase_form_action', raise_if_not_found=False)
    if purchase_form_action:
        purchase_form_action.domain = "[('state', 'in', ('purchase', 'done')), ('is_advance_report', '=', False)]"


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    account_action = env.ref('account.action_move_in_invoice_type', raise_if_not_found=False)
    if account_action:
        account_action.write({
            'domain': "[('move_type', '=', 'in_invoice')]",
            'context': "{'default_move_type': 'in_invoice'}",
        })

    purchase_rfq_action = env.ref('purchase.purchase_rfq', raise_if_not_found=False)
    if purchase_rfq_action:
        purchase_rfq_action.domain = "[]"

    purchase_form_action = env.ref('purchase.purchase_form_action', raise_if_not_found=False)
    if purchase_form_action:
        purchase_form_action.domain = "[('state', 'in', ('purchase', 'done'))]"
