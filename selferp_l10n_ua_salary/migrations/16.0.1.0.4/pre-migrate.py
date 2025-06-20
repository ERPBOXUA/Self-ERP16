from datetime import timedelta

from odoo import fields, api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    def _fix_duplicated_values(table_name, uniq_field_name, next_value, value_to_db):
        env.cr.execute(f"SELECT id, {uniq_field_name} FROM {table_name} GROUP BY {uniq_field_name}, id")
        last_value = None
        fixed_values = set()
        for rec_id, rec_value in env.cr.fetchall():
            if rec_value != last_value and rec_value not in fixed_values:
                fixed_values.add(rec_value)
                last_value = rec_value
            else:
                new_value = rec_value
                while True:
                    new_value = next_value(new_value)
                    if new_value not in fixed_values:
                        env.cr.execute(f"UPDATE {table_name} SET {uniq_field_name} = '{value_to_db(new_value)}' WHERE id={rec_id}")
                        fixed_values.add(new_value)
                        last_value = new_value
                        break

    _fix_duplicated_values(
        'hr_salary_cost_of_living',
        'date',
        lambda d: d + timedelta(days=1),
        lambda d: fields.Date.to_string(d),
    )
    _fix_duplicated_values(
        'hr_salary_disability_group',
        'code',
        lambda c: '%s.copy' % c,
        lambda c: c,
    )
    _fix_duplicated_values(
        'hr_salary_disability_group',
        'name',
        lambda n: '%s (copy)' % n,
        lambda n: n,
    )
    _fix_duplicated_values(
        'hr_salary_inflation_index',
        'date',
        lambda d: d + timedelta(days=1),
        lambda d: fields.Date.to_string(d),
    )
    _fix_duplicated_values(
        'hr_salary_minimum_wage',
        'date',
        lambda d: d + timedelta(days=1),
        lambda d: fields.Date.to_string(d),
    )
    _fix_duplicated_values(
        'hr_salary_sick_leave_rate',
        'name',
        lambda n: '%s (copy)' % n,
        lambda n: n,
    )
