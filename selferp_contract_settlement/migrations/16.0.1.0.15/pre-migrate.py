def migrate(cr, version):
    cr.execute('''
        UPDATE account_report
           SET search_template = 'account_reports.search_template'
         WHERE search_template = 'selferp_contract_settlement.partner_ledger_search_template'
    ''')
