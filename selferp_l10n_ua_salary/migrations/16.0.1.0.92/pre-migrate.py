
def migrate(cr, version):

    def _rename_hr_work_entry_type(old_name, new_name):
        cr.execute(f"""
            SELECT COUNT(*) 
              FROM ir_model_data 
             WHERE module = 'selferp_l10n_ua_salary' 
               AND model = 'hr.work.entry.type' 
               AND name = '{new_name}'
        """)
        rec_count = cr.dictfetchall()[0].get('count')
        if rec_count:
            cr.execute(f"""
                DELETE 
                  FROM ir_model_data 
                 WHERE module = 'selferp_l10n_ua_salary' 
                   AND model = 'hr.work.entry.type' 
                   AND name = '{old_name}'
            """)
        else:
            cr.execute(f"""
                UPDATE ir_model_data
                   SET name = '{new_name}'
                 WHERE module = 'selferp_l10n_ua_salary' 
                   AND model = 'hr.work.entry.type' 
                   AND name = '{old_name}'
            """)

    _rename_hr_work_entry_type('work_entry_type_business_trip', 'hr_work_entry_type_business_trip')
    _rename_hr_work_entry_type('hr_work_entry_annual_additional_leave', 'hr_work_entry_type_annual_additional_leave')
    _rename_hr_work_entry_type('work_entry_type_leave_legal', 'hr_work_entry_type_leave_legal')
