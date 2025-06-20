from odoo import api, models, fields


class AccountAnalyticPlanTemplate(models.Model):
    _name = 'account.analytic.plan.template'
    _description = "Account analytic plan template"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name asc'

    name = fields.Char(
        required=True,
        string="Name",
    )
    description = fields.Text(
        string="Description",
    )
    default_applicability = fields.Selection(
        selection=[
            ('optional', "Optional"),
            ('mandatory', "Mandatory"),
            ('unavailable', "Unavailable"),
        ],
        required=True,
        default='optional',
        string="Default Applicability",
    )
    parent_id = fields.Many2one(
        comodel_name='account.analytic.plan.template',
        domain="[('id', '!=', id)]",
        ondelete='cascade',
        string="Parent",
    )
    parent_path = fields.Char(
        index='btree',
        unaccent=False,
    )
    children_ids = fields.One2many(
        comodel_name='account.analytic.plan.template',
        inverse_name='parent_id',
        string="Children",
    )
    complete_name = fields.Char(
        string="Complete Name",
        compute='_compute_complete_name',
        recursive=True,
        store=True,
    )
    account_template_ids = fields.One2many(
        comodel_name='account.analytic.account.template',
        inverse_name='plan_template_id',
        string="Account Templates",
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for plan in self:
            if plan.parent_id:
                plan.complete_name = '%s / %s' % (plan.parent_id.complete_name, plan.name)
            else:
                plan.complete_name = plan.name

    @api.model
    def create_analytic_plan(self, companies, root_template_xml_id):
        plan_template = self.env.ref(root_template_xml_id)
        if not plan_template:
            return

        for company in companies:
            company_plan_count = self.env['account.analytic.plan'].search_count([
                ('plan_template_id', '=', plan_template.id),
                ('company_id', '=', company.id),
            ])
            if company_plan_count:
                continue

            # load templates from root
            plan_template.with_company(company)._load_template(company)

    def _load_template(self, company, parent=None):
        AccountAnalyticPlan = self.env['account.analytic.plan']
        AccountAnalyticAccount = self.env['account.analytic.account']

        for plan_template in self:
            plan = AccountAnalyticPlan.create(plan_template._get_plan_vals(company, parent))

            # load accounts (if exists)
            if plan_template.account_template_ids:
                for account_template in plan_template.account_template_ids:
                    AccountAnalyticAccount.create(
                        {
                            'company_id': company.id,
                            'name': account_template.name,
                            'code': account_template.code,
                            'description': account_template.description,
                            'plan_id': plan.id,
                        }
                    )

            # load children templates
            if plan_template.children_ids:
                plan_template.children_ids._load_template(company, parent=plan)

    def _get_plan_vals(self, company, parent):
        self.ensure_one()

        return {
            'company_id': company.id,
            'parent_id': parent and parent.id or False,
            'name': self.name,
            'description': self.description,
            'default_applicability': self.default_applicability,
            'plan_template_id': self.id,
            'legacy_plan': False,
        }
