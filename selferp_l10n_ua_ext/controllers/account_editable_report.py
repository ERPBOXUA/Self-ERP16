import io
import zipfile

from collections import defaultdict, OrderedDict
from werkzeug.exceptions import NotFound

from odoo.http import route, request, Controller, content_disposition
from odoo.tools import float_round


def _check_value(value, report):
    if value is not None and isinstance(value, str):
        value = value.strip()
        if not value:
            return ''

        # TODO rewrite this ugly hack!!!!
        if report._name == 'account.vat.tax_report':
            if value.lstrip('-').replace(' ', '').replace(',', '').replace('.', '').isdigit():
                try:
                    value = value.replace(' ', '').replace(',', '.')
                    value = float_round(float(value), precision_digits=0, rounding_method='HALF-UP')
                    return int(value)
                except:
                    pass

    return value


class AccountEditableReportController(Controller):

    @route('/editable_report/edit/<string:report_model>/<int:report_id>/<string:report_part>', auth='user', website=True, sitemap=False)
    def editable_report_edit(self, report_model, report_id, report_part, **kwargs):
        # get report record
        report = self._get_editable_report(report_model, report_id, access='write')
        if not report:
            raise NotFound()

        # prepare render params
        render_params = {
            'report_part': report_part,
            'report_id': report.id,
            'report_part_title': report._get_part_title(report_part),
            'report_part_template': report._get_part_report_name(report_part),
            'report_saved': False,
        }

        # check submit
        if request.httprequest.method == 'POST':
            self._editable_report_save(report, kwargs)
            render_params['report_saved'] = True

        # render page
        return request.render(
            'selferp_l10n_ua_ext.editable_report_page_template',
            report._prepare_render_params(edit_mode=True, params=render_params),
        )

    @route('/editable_report/download_pdf/<string:report_model>/<int:report_id>/<string:report_part>', auth='user', sitemap=False)
    def account_vat_tax_report_download_pdf(self, report_model, report_id, report_part, **kwargs):
        # get report record
        report = self._get_editable_report(report_model, report_id, access='read')
        if not report_part or not report:
            raise NotFound()

        IrActionsReport = request.env['ir.actions.report']

        if report_part == 'all':
            parts = report._get_part_names()

            # create data (ZIP)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                # add main part
                pdf = IrActionsReport._render_qweb_pdf_prepare_streams(
                    report._get_part_action_name(parts[0]),
                    {'report_part': parts[0]},
                    report.ids,
                )
                zip_file.writestr(f'{report.name} - {parts[0]}.pdf', pdf[report.id]['stream'].getvalue())

                # add all marked appendixes
                for doc_key in parts[1:]:
                    field_name = f'include_{doc_key}'
                    if not report._fields.get(field_name) or report[field_name]:
                        pdf = IrActionsReport._render_qweb_pdf_prepare_streams(
                            report._get_part_action_name(doc_key),
                            {'report_part': doc_key},
                            report.ids,
                        )
                        zip_file.writestr(f'{report.name} - {doc_key}.pdf', pdf[report.id]['stream'].getvalue())

            # get ZIP data
            zip_data = zip_buffer.getvalue()

            # determine file name
            zip_name = f'{report.name}.zip'

            # return result
            return request.make_response(
                zip_data,
                headers={
                    ('Content-Type', 'application/zip'),
                    ('Content-Length', len(zip_data)),
                    ('Content-Disposition', content_disposition(zip_name)),
                },
            )

        else:
            # render data
            pdf = IrActionsReport._render_qweb_pdf_prepare_streams(
                report._get_part_action_name(report_part),
                {'report_part': report_part},
                report.ids,
            )
            data = pdf[report.id]['stream'].getvalue()

            # return result
            return request.make_response(
                data,
                headers={
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', len(data)),
                    ('Content-Disposition', content_disposition(f'{report.name} - {report_part}.pdf')),
                },
            )

    @route('/editable_report/download_xml/<string:report_model>/<int:report_id>/<string:report_part>', auth='user', sitemap=False)
    def account_vat_tax_report_download_xml(self, report_model, report_id, report_part, **kwargs):
        # get report record
        report = self._get_editable_report(report_model, report_id, access='read')
        if not report_part or not report:
            raise NotFound()

        if report_part == 'all':
            parts = report._get_part_names()

            # create data (ZIP)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                # add main part
                file_name, data = report.generate_xml(parts[0])
                zip_file.writestr(file_name, data)

                # add all marked appendixes
                for doc_key in parts[1:]:
                    field_name = f'include_{doc_key}'
                    if not report._fields.get(field_name) or report[field_name]:
                        file_name, data = report.generate_xml(doc_key)
                        zip_file.writestr(file_name, data)

            # get ZIP data
            zip_data = zip_buffer.getvalue()

            # determine file name
            zip_name = f'{report.name}.zip'

            # return result
            return request.make_response(
                zip_data,
                headers={
                    ('Content-Type', 'application/zip'),
                    ('Content-Length', len(zip_data)),
                    ('Content-Disposition', content_disposition(zip_name)),
                },
            )

        else:
            # create data (single XML)
            file_name, data = report.generate_xml(report_part)

            # return result
            return request.make_response(
                data,
                headers={
                    ('Content-Type', 'application/xml'),
                    ('Content-Length', len(data)),
                    ('Content-Disposition', content_disposition(file_name)),
                },
            )

    def _get_editable_report(self, report_model, report_id, access='write'):
        # get report
        report = request.env[report_model].browse(report_id).exists()

        # force check report company
        report_sudo = report.sudo()
        if report_sudo.company_id and report_sudo.company_id in request.env.user.company_ids:
            report = report.with_company(report_sudo.company_id)

        # check user access rights
        if report:
            report.check_access_rights(access)
            report.check_access_rule(access)

        return report

    def _editable_report_save(self, report, kwargs):
        # sanitize values
        kwargs.pop('csrf_token', None)

        if kwargs:
            values_update = {}

            # find tables
            table_names = [k for k in kwargs.keys() if k.startswith('J') and '_T' in k and k.endswith('XXXX')]
            tables = {table_name: defaultdict(dict) for table_name in table_names}

            for name, value in kwargs.items():
                if name in table_names:
                    continue

                # is it table cell value?
                current_table_name = None
                for table_name in table_names:
                    if name.startswith(table_name):
                        current_table_name = table_name
                        break

                if current_table_name:
                    # put cell value
                    table = tables[current_table_name]
                    part_name, cell_name, row_num = name.split('_')
                    table[int(row_num)][cell_name] = _check_value(value, report)

                else:
                    # remember non-table value
                    values_update[name] = _check_value(value, report)

            # prepare and remember table value
            for table_name in table_names:
                # sort table by row number
                table = tables[table_name]
                if len(table) > 1:
                    table = OrderedDict(sorted(table.items()))

                # remove empty rows
                table_values = []
                for row in table.values():
                    for cell in row.values():
                        if cell is not None and cell != '':
                            table_values.append(row)
                            break

                # set table values
                values_update[table_name] = table_values

            # update existing values
            values = report.values or {}
            values.update(values_update)

            # just write updated values
            report.values = values
