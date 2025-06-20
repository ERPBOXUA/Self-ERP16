CODES = [
    'ТВ',
    'ВД',
    'Д',
    'ІН',
]


def migrate(cr, version):
    cr.execute(f'''
        UPDATE hr_work_entry_type
           SET timesheet_ccode = CONCAT('_', timesheet_ccode), code = CONCAT('_', code)
         WHERE timesheet_ccode = ANY(%s)  
    ''', (CODES,))
