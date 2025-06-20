import logging

from collections import OrderedDict, defaultdict

from odoo import api, models, fields, _

from odoo.exceptions import UserError
from odoo.tools import float_round

from ..utils.export_xml import export_xml_extract_doc_number, export_xml_create_base_head, export_xml_file_name, xml_prettify, export_xml_match_values_with_schema


_logger = logging.getLogger(__name__)


def round_amount(value):
    value = value or 0
    if value:
        value = float_round(value, precision_digits=0, rounding_method='HALF-UP')
    return int(value)


def to_float(value):
    if not value:
        return 0
    else:
        return float(value)


def sum_amount_float(records, field_name):
    result = 0.0
    if records:
        for record in records:
            result += to_float((record.get(field_name) if isinstance(record, dict) else record[field_name]) or 0)
    return result


def sum_amount_float_by_condition(records, field_name, condition):
    result = 0.0
    if records:
        for record in records:
            if condition(record):
                result += to_float((record.get(field_name) if isinstance(record, dict) else record[field_name]) or 0)
    return result


def sum_amount(records, field_name):
    result = 0.0
    if records:
        for record in records:
            result += to_float((record.get(field_name) if isinstance(record, dict) else record[field_name]) or 0)
    return round_amount(result)


def sum_amount_by_condition(records, field_name, condition):
    result = 0.0
    if records:
        for record in records:
            if condition(record):
                result += to_float((record.get(field_name) if isinstance(record, dict) else record[field_name]) or 0)
    return round_amount(result)


def sum_all_by_keys(values, keys, doc_key=None):
    doc_prefix = ''
    if doc_key:
        doc_prefix = '%s_' % doc_key

    result = 0
    if values and keys:
        result = sum([int(values.get(doc_prefix + k) or 0) for k in keys])

    return round_amount(result)


def prepend_doc_key(values, doc_key):
    if values and doc_key:
        prefix = doc_key + '_'
        new_values = OrderedDict()

        for key, value in values.items():
            if not key.startswith(prefix):
                key = prefix + key
            new_values[key] = value

        values = new_values

    return values


def put_doc_values(values, doc_key, doc_values):
    if values and doc_key and doc_values:
        prefix = doc_key + '_'
        new_values = OrderedDict()

        for key, value in doc_values.items():
            if not key.startswith(prefix):
                key = prefix + key
            new_values[key] = value

        values.update(new_values)

    return values


def extract_doc_values(values, doc_key):
    result = OrderedDict()

    if values and doc_key:
        prefix = doc_key + '_'
        prefix_length = len(prefix)

        for key, value in values.items():
            if key.startswith(prefix):
                result[key[prefix_length:]] = value
            elif not (key.startswith('J') and '_' in key):
                result[key] = value

    return result


def check_not_empty_doc(values, doc_key):
    if values and doc_key:
        for key, value in values.items():
            if key.startswith(doc_key) and  key != f'{doc_key}_HNUM1' and value:
                return True

    return False


def count_unique(records, field_name):
    result_set = set()
    if records:
        for record in records:
            if record.get(field_name):
                result_set.add(record.get(field_name))
    return len(result_set)


def count_unique_condition(records, field_name, condition):
    result_set = set()
    if records:
        for record in records:
            if record.get(field_name) and condition(record):
                result_set.add(record.get(field_name))
    return len(result_set)


class AccountEditableReport(models.AbstractModel):
    _name = 'account.editable.report'
    _description = "Editable Report"
    _order = 'date_from DESC, date_to DESC, id DESC'

    name = fields.Char(
        string="Name",
        required=True,
        default='/',
        readonly=True,
        copy=False,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        ondelete='restrict',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        string="Company",
    )

    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('generated', "Generated"),
            ('cancelled', "Cancelled"),
        ],
        required=True,
        default='draft',
        readonly=True,
        index=True,
        copy=False,
    )

    date_from = fields.Date(
        string="Date from",
        required=True,
    )
    date_to = fields.Date(
        string="Date to",
        required=True,
    )
    date_generate = fields.Datetime(
        string="Document date",
    )

    values = fields.Json(
        string="Values",
        default={},
        copy=False,
    )

    @api.depends('values')
    def _compute_rendered_html_parts(self):
        IrQweb = self.env['ir.qweb']
        docs = self._get_part_names()

        for record in self:
            # prepare report params
            values = self._prepare_render_params(edit_mode=False)

            # render report parts
            for doc in docs:
                field_name = f'rendered_html_part_{doc}'

                if record._fields.get(field_name):
                    doc_value = None
                    if record.state != 'draft':
                        template = self._get_part_report_name(doc)

                        params = dict(**values, **{
                            'report_part': doc,
                            'report_part_template': template,
                        })

                        doc_value = IrQweb._render(template, params)

                    record[field_name] = doc_value

    def write(self, values):
        # recompute values if need
        if not self._context.get('skip_report_recompute_values'):
            if values.get('values'):
                self._recompute_values(values.get('values'))

        # write changes
        result = super().write(values)

        # if 'include' sign changed - analyze if for each record
        if not self._context.get('skip_vat_tax_report_check_included_docs') and any([name.startswith('include_') for name in values.keys()]):
            self._check_included_in_values()

        # return result
        return result

    def unlink(self):
        if self.filtered(lambda r: r.state != 'draft'):
            raise UserError(_("Only draft reports can be removed"))
        super().unlink()

    def action_generate(self):
        self.ensure_one()

        # @TODO: check report existing

        # generate report data
        values = self._generate_data()

        update_values = {
            'state': 'generated',
            'values': values,
        }

        # check additions switched on checkboxes
        # basing on generated data
        self._check_included_by_values(update_values)

        # write changes
        self.write(update_values)

    def action_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancelled',
        })

    def action_reset_to_draft(self):
        self.ensure_one()
        if self.state != 'cancelled':
            raise UserError(_("Only cancelled reports can be reset to draft"))

        self.write({
            'state': 'draft',
            'values': None,
            'date_generate': None,
        })

    def action_edit_part(self):
        part_name = self._ensure_part_name()
        return {
            'name': _("Edit %s", self.name),
            'type': 'ir.actions.act_url',
            'url': f'/editable_report/edit/{self._name}/{self.id}/{part_name}',
            'target': 'new',
        }

    def action_download_pdf(self):
        if self._context.get('editable_report_part_name'):
            part_name = self._ensure_part_name()
            if part_name:
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/editable_report/download_pdf/{self._name}/{self.id}/{part_name}',
                    'target': 'new',
                }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/editable_report/download_pdf/{self._name}/{self.id}/all',
                'target': 'new',
            }

    def action_download_xml(self):
        self.ensure_one()

        if self._context.get('editable_report_part_name'):
            part_name = self._ensure_part_name()
            if part_name:
                self._check_required_values_for_export_xml(part_name)
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/editable_report/download_xml/{self._name}/{self.id}/{part_name}',
                    'target': 'new',
                }

        else:
            self._check_required_values_for_export_xml()
            return {
                'type': 'ir.actions.act_url',
                'url': f'/editable_report/download_xml/{self._name}/{self.id}/all',
                'target': 'new',
            }

    def generate_xml(self, part_name):
        # check part name existing
        self.with_context(editable_report_part_name=part_name)._ensure_part_name()
        self._check_required_values_for_export_xml(part_name)

        doc_name = self._get_doc_name(part_name)

        if self.state != 'generated':
            raise UserError(_("Unexpected document state"))

        # prepare data
        data = defaultdict(lambda: None)

        # get stored data
        data.update(extract_doc_values(self.values, part_name))

        # add header values
        period_type = self._get_period_type()
        period_month = data['HZM']
        period_year = data['HZY']
        data.update(export_xml_create_base_head(
            doc_name,
            self.company_id,
            self._get_doc_num(part_name),
            period_type=period_type,
            period_month=period_month,
            period_year=period_year,
        ))

        # get linked documents info
        docs = self._get_part_names()
        linked_documents = []

        if part_name == docs[0]:
            for doc_key in docs[1:]:
                field_name = f'include_{doc_key}'
                if self._fields.get(field_name) and self[field_name]:
                    linked_document_values = export_xml_create_base_head(
                        doc_key,
                        self.company_id,
                        self._get_doc_num(doc_key),
                        period_type=period_type,
                        period_month=period_month,
                        period_year=period_year,
                    )
                    linked_document_values['TYPE'] = '1'
                    linked_document_values['FILENAME'] = export_xml_file_name(linked_document_values)
                    linked_documents.append(linked_document_values)
        else:
            linked_document_values = export_xml_create_base_head(
                docs[0],
                self.company_id,
                self._get_doc_num(docs[0]),
                period_type=period_type,
                period_month=period_month,
                period_year=period_year,
            )
            linked_document_values['TYPE'] = '2'
            linked_document_values['FILENAME'] = export_xml_file_name(linked_document_values)
            linked_documents.append(linked_document_values)

        # update other values
        data.update({
            'LINKED_DOCS': linked_documents or None,
            'D_FILL': data['HFILL'],
        })

        # analyze and convert values for XML
        data = export_xml_match_values_with_schema(doc_name, data)

        # render XML
        xml_data = self.env['ir.qweb']._render(
            self._get_part_xml_template(part_name),
            {
                'record': self,
                'data': data,
            },
        ).strip()
        xml_data = xml_prettify(xml_data)

        # create file name
        file_name = export_xml_file_name(data)

        # return result
        return file_name, xml_data

    def _prepare_create_values(self, vals_list):
        result_vals_list = super()._prepare_create_values(vals_list)
        for vals in result_vals_list:
            sequence = self._get_editable_report_sequence(vals)
            if sequence:
                vals['name'] = sequence.next_by_id()

        return result_vals_list

    @api.model
    def _get_editable_report_sequence(self, vals_list):
        return None

    @api.model
    def _get_part_names(self):
        """ Returns tuple of all possible document types (including appendixes)

        :return:
        """
        return None

    @api.model
    def _get_doc_name(self, part_name):
        """ Extract related document type from part name.
            Means if it's subset of some document - return main document type.
            For example, if part name is J0510108M2, then main document type is J0510108.

        :param part_name:
        :return:
        """
        return part_name

    def _get_doc_num(self, part_name):
        """ Returns doc number for given part.
            Always returns '1' by default

        :param part_name:
        :return:
        """
        self.ensure_one()
        return '1'

    @api.model
    def _get_part_title(self, part_name):
        """ Return human-readable title of given part (to display on edit page,
            for example)

        :param part_name:
        :return:
        """
        return ''

    @api.model
    def _get_part_action_name(self, part_name):
        """ Returns action's XML-ID of given part

        :param part_name:
        :return:
        """
        return None

    @api.model
    def _get_part_report_name(self, part_name):
        """ Returns report template XML-ID of given part

        :param part_name:
        :return:
        """
        return None

    @api.model
    def _get_part_xml_template(self, part_name):
        """ Returns XML template XML-ID of given part

        :param part_name:
        :return:
        """
        return None

    def _check_required_values_for_export_xml(self, part_name=None):
        self.ensure_one()

        if not self.company_id.company_registry:
            raise UserError(_("Company ID not defined"))

        if not self.company_id.tax_inspection_id:
            raise UserError(_("Tax inspection for company not defined"))

    @api.model
    def _get_period_type(self):
        """ Returns document period type string:
            1 - month
            2 - quarter
            3 - half year
            4 - 9 month
            5 - year

        :param part_name:
        :return:
        """
        return '1'

    def _generate_data(self):
        """ Generate data of report

        :return:
        """
        return {}

    def _recompute_values(self, values):
        """ Recompute some values on each report values changes

        :param values:
        :return:
        """
        pass

    def _ensure_part_name(self):
        self.ensure_one()

        part_name = self._context.get('editable_report_part_name')
        if not part_name:
            raise UserError(_("Report part name undefined"))

        return part_name

    def _prepare_render_params(self, edit_mode=False, params=None):
        self.ensure_one()

        result = {
            'edit_mode': edit_mode,
            'values': self.values or {},
        }

        if params:
            result.update(params)

        return result

    def _check_included_in_values(self):
        """ Check 'included' sign changed and apply it for each record

        :param values:
        :return:
        """
        pass

    def _check_included_by_values(self, update_values):
        values = update_values.get('values') or {}
        for doc_key in self._get_part_names()[1:]:
            field_name = f'include_{doc_key}'
            if self._fields.get(field_name):
                update_values[field_name] = check_not_empty_doc(values, doc_key)

    @api.model
    def migrate_data(self, from_version, version_length=2):
        if not self.env.context.get('allow_data_migration'):
            raise UserError(_("Data migration is not allowed"))

        _logger.info("Start data (values) migration")

        # check docs
        docs = self._get_part_names()
        if not docs:
            _logger.info("No any docs for migration specified. Migration finished.")
            return

        # check version
        from_version = str(from_version).zfill(version_length)
        to_version = docs[0][6:6 + version_length]
        if from_version == to_version:
            _logger.info("Version the same, it looks like already migrated. Migration finished.")
            return

        # iterate and migrate all data
        records = self.with_context(active_test=False).search([
            ('values', '!=', False),
        ])
        for record in records:
            values = record.values

            if values:
                new_values = {}

                for doc_key_new in docs:
                    doc_key_old = doc_key_new[:6] + from_version + doc_key_new[6 + version_length:]
                    doc_key_old_length = len(doc_key_old)

                    for key, value in values.items():
                        if key.startswith(doc_key_old):
                            new_values[f'{doc_key_new}{key[doc_key_old_length:]}'] = value
                        else:
                            new_values[key] = value

                record.values = new_values

        _logger.info("Migration finished.")
