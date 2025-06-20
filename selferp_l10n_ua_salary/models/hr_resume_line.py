from odoo import api, fields, models


class ResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    diploma = fields.Char(
        string="Diploma",
        help="Diploma, series, number",
    )

    diploma_speciality = fields.Char(
        string="Speciality/profession",
        help="Speciality/profession by diploma",
    )

    diploma_qualification = fields.Char(
        string="Qualification",
        help="Qualification by diploma",
    )

    study_form = fields.Selection(
        selection=[
            ('full_time', "Full-time education"),
            ('evening_form', "Evening form of study"),
            ('external_form', "External form of education"),
        ],
        string="Form of Study",
    )

    education_type = fields.Selection(
        selection=[
            ('1_basic_general_secondary', "Basic General Secondary"),
            ('2_complete_general_secondary', "Complete General Secondary"),
            ('3_vocational', "Vocational"),
            ('4_incomplete_higher', "Incomplete Higher"),
            ('5_basic_higher', "Basic Higher"),
            ('6_complete_higher', "Complete Higher"),
        ],
        string="Education Type",
    )

    post_graduate_education = fields.Selection(
        selection=[
            ('1_post_higher_edu', "Post Higher Education"),
            ('2_adjunct', "Adjunct"),
            ('3_doctoral_edu', "Doctoral Studies"),
        ],
        string="Post-graduate education",
    )

    diploma_num_state = fields.Char(
        string="Diploma, number and date",
        help="Diploma, number and date of issue",
    )
    scientific_degree = fields.Char(
        string="Scientific Degree",
    )

    job_position = fields.Char(
        string="Job  position",
    )
    dismissal_reason = fields.Selection(
        selection=[
            ('redundancy', "Redundancy"),
            ('dismiss_at_will', "Dismiss at will"),
            ('absenteeism_and_other_violations', "Absenteeism and Other Violations"),
            ('incompetence', "Incompetence"),
        ],
        string="Dismissal reason",
    )

    company_expense_education_date = fields.Date(
        string="Date",
    )
    company_expense_education_name = fields.Char(
        string="The name of the structural division",
    )
    company_expense_education_period = fields.Char(
        string="Education date",
    )
    company_expense_education_type = fields.Char(
        string="Education type",
    )
    company_expense_education_form = fields.Char(
        string="Education form",
    )
    company_expense_education_document = fields.Char(
        string="Document name",
        help="Document name certifying professional education, by whom issued",
    )

    is_education_fields_visible = fields.Boolean(
        compute='_compute_is_line_type_id_selected',
    )

    is_experience_fields_visible = fields.Boolean(
        compute='_compute_is_line_type_id_selected',
    )

    is_post_graduate_fields_visible = fields.Boolean(
        compute='_compute_is_line_type_id_selected',
    )

    is_education_company_expense_fields_visible = fields.Boolean(
        compute='_compute_is_line_type_id_selected',
    )

    @api.onchange('line_type_id')
    def _compute_is_line_type_id_selected(self):
        education = self.env.ref('hr_skills.resume_type_education')
        experience = self.env.ref('hr_skills.resume_type_experience')
        post_graduate = self.env.ref('selferp_l10n_ua_salary.hr_resume_line_type_post_graduate')
        education_company_expense = self.env.ref('selferp_l10n_ua_salary.hr_resume_line_type_education_company_expense')

        for rec in self:
            rec.is_education_fields_visible = rec.line_type_id == education
            rec.is_experience_fields_visible = rec.line_type_id == experience
            rec.is_post_graduate_fields_visible = rec.line_type_id == post_graduate
            rec.is_education_company_expense_fields_visible = rec.line_type_id == education_company_expense
