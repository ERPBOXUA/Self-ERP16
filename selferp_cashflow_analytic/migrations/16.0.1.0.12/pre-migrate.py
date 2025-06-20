def migrate(cr, version):
    cr.execute('''
        DELETE FROM ir_model_data 
         WHERE module = 'selferp_cashflow_analytic' 
           AND model = 'account_analytic_plan';
    ''')
