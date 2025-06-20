from odoo import api, SUPERUSER_ID


def _rename_field(env, table_name):
    env.cr.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN IF NOT EXISTS account_in_next_period BOOLEAN
    """)
    env.cr.execute(f"""
        COMMENT ON COLUMN {table_name}.account_in_next_period IS 'Take Into Account In Next Period'
    """)
    env.cr.execute(f"""
        UPDATE {table_name} SET account_in_next_period = account_in_previous_period
    """)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _rename_field(env, 'hr_payroll_contract_benefit')
    _rename_field(env, 'hr_payslip_benefit_line')
