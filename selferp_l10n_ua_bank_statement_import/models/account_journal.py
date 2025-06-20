import datetime
import io
import xlrd

from odoo import models, fields, _
from odoo.tools import pycompat
from odoo.tools import safe_eval
from odoo.exceptions import UserError


MIMETYPE_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    import_mapping_id = fields.Many2one(
        comodel_name='account.bank.statement.import.mapping',
        string="Import Mapping",
    )

    def _check_csv(self, filename):
        if self and self.import_mapping_id:
            # switch off standard CSV parsing
            return False
        else:
            return super()._check_csv(filename)

    def _parse_bank_statement_file(self, attachment):
        if self and self.import_mapping_id:
            return getattr(self, f'_parse_bank_statement_file_{self.import_mapping_id.file_type}')(attachment)
        else:
            return super()._parse_bank_statement_file(attachment)

    def _parse_bank_statement_file_xls(self, attachment):
        mapping = self.import_mapping_id

        # open workbook
        book = xlrd.open_workbook(file_contents=attachment.raw, formatting_info=(attachment.mimetype != MIMETYPE_XLSX))

        # get sheet
        sheet = None
        if mapping.sheet_name:
            try:
                sheet = book.sheet_by_name(mapping.sheet_name)
            except:
                try:
                    sheet = book.sheet_by_index(int(mapping.sheet_name.strip()) - 1)
                except:
                    raise UserError(_("Wrong sheet name '%s'") % mapping.sheet_name)
        if not sheet:
            sheet = book.sheet_by_index(0)

        # build columns mapping
        if mapping.use_header:
            headers = sheet.row_values(mapping.row_num_header - 1, start_colx=0, end_colx=None)
            headers = [h.strip() for h in headers]
        else:
            headers = []

        # parse data
        data = []
        for row_index in range(int(mapping.row_num_data) - 1, sheet.nrows):
            values = {}

            for column_index in range(0, sheet.ncols):
                value = sheet.cell_value(row_index, column_index)
                cell = sheet.cell(row_index, column_index)

                if cell.ctype == xlrd.XL_CELL_DATE:
                    value = datetime.datetime(*xlrd.xldate_as_tuple(value, sheet.book.datemode))

                if mapping.use_header:
                    values[headers[column_index]] = value
                else:
                    values[str(column_index + 1)] = value

            data.append(values)

        # prepare result
        return self._parse_bank_statement_file_prepare_result(data)

    def _parse_bank_statement_file_csv(self, attachment):
        mapping = self.import_mapping_id

        # encode data
        data = attachment.raw
        encoding = mapping.encoding or 'utf-8'
        if encoding != 'utf-8':
            data = data.decode(encoding).encode('utf-8')

        # create CSV iterator
        separator = ','
        if mapping.separator == 'dot':
            separator = '.'
        elif mapping.separator == 'semicolon':
            separator = ';'
        elif mapping.separator == 'tab':
            separator = '\t'
        elif mapping.separator == 'space':
            separator = ' '

        csv_iterator = pycompat.csv_reader(
            io.BytesIO(data),
            quotechar=mapping.text_delimiter or '"',
            delimiter=separator
        )

        # read CSV
        content = [row for row in csv_iterator]

        # get headers
        if mapping.use_header:
            headers = content[mapping.row_num_header - 1]
            headers = [h.strip() for h in headers]
        else:
            headers = []

        # parse data
        data = []
        for row_index in range(int(mapping.row_num_data) - 1, len(content)):
            row = content[row_index]

            if any(x for x in row if x.strip()):
                values = {}

                if mapping.use_header:
                    for i, header in enumerate(headers):
                        values[header] = row[i]
                else:
                    for i, header in enumerate(row):
                        values[str(i + 1)] = row[i]

                data.append(values)

        # prepare result
        return self._parse_bank_statement_file_prepare_result(data)

    def _parse_bank_statement_file_prepare_result(self, data):
        Partner = self.env['res.partner'].with_context(active_test=False).sudo()
        mapping = self.import_mapping_id

        transactions = []

        for i, data_row in enumerate(data):
            transaction = {
                'sequence': i + 1,
            }

            for line in mapping.line_ids:
                field_name = line.bank_statement_line_field

                value = None
                column_name = line.column_name and line.column_name.strip() or ''
                if column_name:
                    value = data_row[line.column_name]

                    if value and isinstance(value, str):
                        value = value.strip()

                if line.use_python:
                    params = {
                        # put libraries
                        'datetime': safe_eval.datetime,
                        'dateutil': safe_eval.dateutil,
                        'json': safe_eval.json,
                        'time': safe_eval.time,
                        'pytz': safe_eval.pytz,

                        # put values
                        'field_name': field_name,
                        'value': value,
                        'mapping': mapping,
                        'mapping_line': line,
                        'data': data,
                        'data_row': data_row,
                    }

                    # try to evaluate python script
                    params['result'] = None
                    try:
                        value = safe_eval.safe_eval(line.python_code, params, mode='eval') or params['result']
                    except:
                        safe_eval.safe_eval(line.python_code, params, mode='exec', nocopy=True)
                        value = params['result']

                else:
                    if field_name == 'date':
                        # parse date value
                        if not isinstance(value, datetime.date):
                            value = datetime.datetime.strptime(str(value), line.value_format).date()

                    elif field_name == 'partner_id':
                        # try to find partner record
                        partner = Partner.search([
                            ('company_registry', '=', str(value)),
                        ], limit=1)

                        if partner:
                            value = partner.id
                        else:
                            # just skip and do not set field value
                            continue

                    elif field_name == 'amount' and not isinstance(value, (int, float)):
                        value = str(value).strip()
                        if mapping.decimal_separator != 'dot':
                            value = value.replace('.', '').replace(',', '.')
                        else:
                            value = value.replace(',', '')
                        value = float(value)

                # set value
                transaction[field_name] = value

            # add transaction
            transactions.append(transaction)

        # return result
        return None, None, [{
            'transactions': transactions,
        }]

