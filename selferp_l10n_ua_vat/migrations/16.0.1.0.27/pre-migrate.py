from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.flush_all()
    env.cr.execute('''
        DELETE 
          FROM ir_model_fields
         WHERE model_id IN (
               SELECT id 
                 FROM ir_model 
                WHERE ir_model.model = 'account.move.vat.adjustment.line'
               )
    ''')

    env.cr.execute('''
        DELETE
          FROM ir_model_access
         WHERE model_id IN (
               SELECT id 
                 FROM ir_model 
                WHERE ir_model.model = 'account.move.vat.adjustment.line'
               )
    ''')

    env.cr.execute('''
        DELETE
          FROM ir_model
         WHERE model = 'account.move.vat.adjustment.line'
    ''')
