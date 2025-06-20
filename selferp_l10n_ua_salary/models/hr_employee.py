from odoo import api, models, fields, _
from odoo.tools import config


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sick_leave_rate_ids = fields.One2many(
        comodel_name='hr.employee.sick_leave.rate',
        inverse_name='employee_id',
        string="Sick Leave Rates",
    )

    disability_group_ids = fields.One2many(
        comodel_name='hr.employee.disability_group',
        inverse_name='employee_id',
        string="Disability Groups",
    )

    tax_social_benefit_ids = fields.One2many(
        comodel_name='hr.employee.tax_social_benefit',
        inverse_name='employee_id',
        string="Tax Social Benefits",
    )

    employment_type = fields.Selection(
        selection=[
            ('employment_main_place', "Employment main place"),
            ('civil_law_contract', "Civil law contract"),
            ('external_part_time', "External part-time"),
            ('internal_part_time', "Internal part-time"),
        ],
        string="Employment type",
    )

    order_ids = fields.One2many(
        comodel_name='hr.order',
        inverse_name='employee_id',
        string="Employee Orders",
    )

    orders_count = fields.Integer(
        string="Orders count",
        compute='_compute_orders_count',
    )

    hire_date = fields.Date(
        string="Hire date",
    )

    is_retiring = fields.Boolean(
        string="Is retiring",
    )

    information_on_receiving_pensions = fields.Char(
        string="Information on receiving pensions",
    )

    is_equal_to_registration_address = fields.Boolean(
        string="Home address is equal to registration address",
    )

    registration_address = fields.Char(
        string="Registration address",
    )

    register_uit = fields.Char(
        string="Register uit",
    )

    fit_for_military_service = fields.Char(
        string="Fit for military service",
    )

    category_unit = fields.Char(
        string="Category unit",
    )

    commissariat_at_registration = fields.Char(
        string="Commissariat at registration",
    )

    rank_group = fields.Char(
        string="Rank group",
    )

    commissariat_at_home_address = fields.Char(
        string="Commissariat at home address",
    )

    military_rank = fields.Char(
        string="Military rank",
    )

    military_registration_speciality_no = fields.Char(
        string="Military registration speciality No.",
    )

    staying_on_a_special_register = fields.Char(
        string="Staying on a special register",
    )

    passport_series = fields.Char(
        string="Passport series",
    )

    passport_issuing_authority = fields.Char(
        string="Passport issuing authority",
    )

    passport_issue_date = fields.Date(
        string="Passport issue date",
    )

    passport_validity_date = fields.Date(
        string="Passport validity date",
    )

    hr_position_id = fields.Many2one(
        comodel_name='hr.employee',
        string="HR position",
    )

    family_ids = fields.One2many(
        comodel_name='hr.employee.family',
        inverse_name='family_id',
        string="Family",
    )

    work_experience_days = fields.Char(
        string="Days",
    )

    work_experience_months = fields.Char(
        string="Months",
    )

    work_experience_years = fields.Char(
        string="Years",
    )

    name = fields.Char(
        compute="_compute_name",
        inverse="_inverse_name",
    )

    first_name = fields.Char(
        string="First name",
    )

    last_name = fields.Char(
        string="Last name",
    )

    patronymic = fields.Char(
        string="Patronymic",
    )

    is_labor_book = fields.Boolean(
        string="Keep Labor Book",
        default=False,
    )

    tests_enabled = fields.Boolean(
        compute='_compute_tests_enabled',
        default=lambda self: config['test_enable'],
    )

    @api.depends('first_name', 'last_name', 'patronymic')
    @api.onchange('first_name', 'last_name', 'patronymic')
    def _compute_name(self):
        for rec in self:
            rec.name = rec._merge_name(rec.last_name, rec.first_name, rec.patronymic)

    @api.depends('name')
    def _inverse_name(self):
        for record in self:
            if record.name:
                parts = self._split_name(record.name)
                if parts:
                    record.last_name = parts.get('last_name')
                    record.first_name = parts.get('first_name')
                    record.patronymic = parts.get('patronymic')

    def _check_date_not_before_hire_date(self, date):
        if date:
            first_contract = self.get_first_contract()
            hire_date = first_contract and first_contract.date_start or None
            if hire_date and date.year == hire_date.year and date.month == hire_date.month and hire_date > date:
                date = hire_date
        return date

    def _compute_tests_enabled(self):
        test_enable = config['test_enable']
        for rec in self:
            rec.tests_enabled = test_enable

    def has_actual_disability_group(self, date):
        self.ensure_one()
        if self.disability_group_ids and date:
            date = self._check_date_not_before_hire_date(date)
            disability_groups = self.disability_group_ids.sorted(key=lambda grp: grp.apply_date)
            max_group = len(disability_groups) - 1
            if date >= disability_groups[0].apply_date:
                for i in range(max_group + 1):
                    range_start = disability_groups[i].apply_date
                    range_end = disability_groups[i + 1].apply_date if i < max_group else date.max
                    if range_start <= date < range_end:
                        return disability_groups[i].disability_group_id.code in ('I', 'II', 'III')
        return False

    def get_tax_social_benefit(self, date_from, date_to):
        self.ensure_one()
        if self.tax_social_benefit_ids and date_from and date_to:
            date_from = self._check_date_not_before_hire_date(date_from)
            # TODO: do we need to check fire date?
            tax_social_benefit = self.tax_social_benefit_ids.filtered(
                lambda rec: date_from >= rec.date_from and date_to <= rec.date_to
            )
            return tax_social_benefit
        return None

    def write(self, vals):
        # compute does not work in this case
        self._prepare_vals(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._prepare_vals(vals)

        return super().create(vals_list)

    @api.model
    def _split_name(self, name):
        name_wo_double_spaces = ' '.join(name.split())
        parts = name_wo_double_spaces.split(' ', 2)
        if len(parts) == 1:
            return {'last_name': None, 'first_name': parts[0], 'patronymic': None}
        elif len(parts) == 2:
            return {'last_name': parts[0], 'first_name': parts[1], 'patronymic': None}
        elif len(parts) > 2:
            return {'last_name': parts[0], 'first_name': parts[1], 'patronymic': parts[2]}
        return None

    def _merge_name(self, last_name, first_name, patronymic=None):
        names = list()
        if last_name:
            names.append(last_name)
        if first_name:
            names.append(first_name)
        if patronymic:
            names.append(patronymic)
        if len(names):
            return ' '.join(names)
        return None

    def _prepare_vals(self, vals):
        if not vals.get('name') and (vals.get('first_name') or vals.get('last_name') or vals.get('patronymic')):
            if vals.get('last_name'):
                last_name = vals.get('last_name')
            else:
                last_name = self.last_name or ''
            if vals.get('first_name'):
                first_name = vals.get('first_name')
            else:
                first_name = self.first_name or ''
            if vals.get('patronymic'):
                patronymic = vals.get('patronymic')
            else:
                patronymic = self.patronymic

            vals['name'] = self._merge_name(last_name, first_name, patronymic)

        elif vals.get('name') and not vals.get('first_name') and not vals.get('last_name') and not vals.get('patronymic'):
            parts = self._split_name(vals.get('name'))
            if parts:
                vals.update(parts)

    @api.model
    def _install_employee_firstname_lastname_patronymic(self):
        records = self.search([('first_name', '=', False), ('last_name', '=', False), ('patronymic', '=', False)])
        records._inverse_name()

    def _read(self, fields):
        fixed_fields = fields
        if not self.check_access_rights('read', raise_exception=False):
            fixed_fields = list(filter(lambda field: not self._fields[field]._module.startswith('selferp'), fields))
        return super()._read(fixed_fields)

    def _compute_orders_count(self):
        for employee in self:
            employee.orders_count = len(employee.order_ids)

    def action_open_employee_orders(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Orders"),
            'res_model': 'hr.order',
            'domain': [
                ('employee_id', '=', self.id),
            ],
            'view_mode': 'tree,form',
            'context': {'default_employee_id': self.id},
        }

    def get_first_contract(self):
        self.ensure_one()
        contracts = self.contract_ids.filtered(lambda rec: rec.state in ('open', 'close')).sorted('date_start')
        return contracts and contracts[0] or None
