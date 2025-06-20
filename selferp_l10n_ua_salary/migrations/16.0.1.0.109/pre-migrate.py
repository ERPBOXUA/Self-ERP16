from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.cr.execute("""
        ALTER TABLE hr_salary_cost_of_living
        ADD COLUMN IF NOT EXISTS value_children_under_6 NUMERIC
    """)
    env.cr.execute("""
        COMMENT ON COLUMN hr_salary_cost_of_living.value_children_under_6 IS 'Value For Children Under 6 y.o.'
    """)

    env.cr.execute("""
        ALTER TABLE hr_salary_cost_of_living
        ADD COLUMN IF NOT EXISTS value_children_from_6_to_18 NUMERIC
    """)
    env.cr.execute("""
        COMMENT ON COLUMN hr_salary_cost_of_living.value_children_from_6_to_18 IS 'Value For Children From 6 To 18 y.o.'
    """)

    env.cr.execute("""
        INSERT INTO hr_salary_cost_of_living ("date", "value", "value_children_under_6", "value_children_from_6_to_18")
             VALUES ('2023-01-01', 2684.0, 2272.0, 2833.0) 
        ON CONFLICT ("date") 
                 DO
             UPDATE
                SET "value" = 2684.0, "value_children_under_6" = 2272.0, "value_children_from_6_to_18" = 2833.0
    """)

    env.cr.execute("""
        INSERT INTO hr_salary_cost_of_living ("date", "value", "value_children_under_6", "value_children_from_6_to_18")
             VALUES ('2022-12-01', 2684.0, 2272.0, 2833.0) 
        ON CONFLICT ("date") 
                 DO
             UPDATE
                SET "value" = 2684.0, "value_children_under_6" = 2272.0, "value_children_from_6_to_18" = 2833.0
    """)

    env.cr.execute("""
            INSERT INTO hr_salary_cost_of_living ("date", "value", "value_children_under_6", "value_children_from_6_to_18")
                 VALUES ('2022-07-01', 2600.0, 2201.0, 2744.0) 
            ON CONFLICT ("date") 
                     DO
                 UPDATE
                    SET "value" = 2600.0, "value_children_under_6" = 2201.0, "value_children_from_6_to_18" = 2744.0
        """)

    env.cr.execute("""
            INSERT INTO hr_salary_cost_of_living ("date", "value", "value_children_under_6", "value_children_from_6_to_18")
                 VALUES ('2022-01-01', 2481.0, 2100.0, 2618.0) 
            ON CONFLICT ("date") 
                     DO
                 UPDATE
                    SET "value" = 2481.0, "value_children_under_6" = 2100.0, "value_children_from_6_to_18" = 2618.0
        """)
