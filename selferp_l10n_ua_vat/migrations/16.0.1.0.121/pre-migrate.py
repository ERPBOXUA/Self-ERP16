from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.cr.execute('''
        DELETE 
          FROM ir_ui_view 
         WHERE id IN (
               SELECT res_id 
                 FROM ir_model_data 
                WHERE model = 'ir.ui.view' 
                  AND module IN ('selferp_analytic_sale_order', 'selferp_analytic_purchase_order')
         )
    ''')

    env.cr.execute('''
        DELETE 
          FROM ir_model_fields
         WHERE id IN (
               SELECT res_id 
                 FROM ir_model_data 
                WHERE name ILIKE 'field_%' 
                  AND module IN ('selferp_analytic_sale_order', 'selferp_analytic_purchase_order')
         )
    ''')

    env.cr.execute('''
        DELETE 
          FROM ir_module_module_dependency 
         WHERE name IN ('selferp_analytic_sale_order', 'selferp_analytic_purchase_order')
    ''')

    env.cr.execute('''
        DELETE
          FROM ir_module_module 
         WHERE name IN ('selferp_analytic_sale_order', 'selferp_analytic_purchase_order');
    ''')
