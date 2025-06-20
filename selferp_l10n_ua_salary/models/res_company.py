from odoo import api, models, fields


SALARY_ADVANCE_VARIANTS = [
    ('first_15_days', "First 15 Days"),
    ('percentage', "Salary Percentage"),
]

PRECISION_SALARY_ADVANCE_PERCENTAGE = (16, 3)


class ResCompany(models.Model):
    _inherit = 'res.company'

    salary_advance_calculation = fields.Selection(
        selection=SALARY_ADVANCE_VARIANTS,
        string="Salary Advance Calculation",
        default='first_15_days',
    )

    salary_advance_percents = fields.Float(
        string="Salary Percentage",
        digits=PRECISION_SALARY_ADVANCE_PERCENTAGE,
        default=0.5,
    )

    sequence_pdfo_report_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Sequence of PDFO Report",
    )

    salary_indexation_period_ids = fields.One2many(
        comodel_name='salary.indexation_period',
        inverse_name='company_id',
        string="Salary Indexation Periods",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # create companies
        companies = super().create(vals_list)

        # setup sequences
        companies._setup_pdfo_sequences()

        for company in companies:
            for order_type_group in self.env['hr.order.type.group'].search([]):
                order_type_group.with_company(company).property_sequence_id = order_type_group.create_order_type_group_sequence(company.id)
        return companies

    def unlink(self):
        # remove sequences
        self.mapped('sequence_pdfo_report_id').unlink()
        # remove companies
        return super().unlink()

    def _setup_pdfo_sequences(self):
        sequence = self.env.ref('selferp_l10n_ua_salary.seq_hr_pdfo_report', raise_if_not_found=False)
        if sequence:
            for company in self:
                if not company.sequence_pdfo_report_id:
                    company.sequence_pdfo_report_id = sequence.copy({
                        'company_id': company.id,
                    })
