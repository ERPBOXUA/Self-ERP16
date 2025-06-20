from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountBankStatementImportMapping(models.Model):
    _name = 'account.bank.statement.import.mapping'
    _description = "Account Bank Statement Import Mapping"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    file_type = fields.Selection(
        selection=[
            ('csv', "CSV"),
            ('xls', "XLS"),
        ],
        string="File Type",
        required=True,
        default='csv',
    )

    line_ids = fields.One2many(
        comodel_name='account.bank.statement.import.mapping.line',
        inverse_name='mapping_id',
        string="Mapping Lines",
        copy=True,
    )
    use_header = fields.Boolean(
        string="Use Header",
        default=True,
    )
    row_num_header = fields.Integer(
        string="Header Row Number",
        help="Header row number (starting from 1)",
        default=1,
    )
    row_num_data = fields.Integer(
        string="Data Start Row Number",
        help="First data row number (starting from 1)",
        required=True,
        default=2,
    )

    decimal_separator = fields.Selection(
        selection=[
            ('dot', "Dot (.)"),
            ('comma', "Comma (,)"),
        ],
        string="Decimal Separator",
        required=True,
        default='dot',
    )

    # XLS-specific settings
    sheet_name = fields.Char(
        string="Sheet Name/Number",
        help="Name of sheet or number (starting from 1)",
        default='1',
    )

    # CSV-specific settings
    encoding = fields.Selection(
        # encodings from https://docs.python.org/3/library/codecs.html#standard-encodings
        selection=[
            ('utf-8', "UTF-8"),
            ('utf-16', "UTF-16"),
            ('utf-32', "UTF-32"),
            ('cp1251', "Windows-1251"),
            ('cp1125', "CP1125"),
            ('cp866', "CP866"),
            ('koir8_u', "KOI8-U"),
            ('koir8_r', "KOI8-R"),
            ('cp855', "CP855"),
            ('cp1252', "Windows-1252"),
            ('ascii', "ASCII"),
            ('latin1', "Latin1"),
            ('latin2', "Latin2"),
            ('big5', "Big-5"),
            ('gb18030', "GB 18030"),
            ('shift_jis', "Shift JIS"),
        ],
        string="Encoding",
        default='utf-8',
    )
    separator = fields.Selection(
        selection=[
            ('comma', "Comma (,)"),
            ('dot', "Dot (.)"),
            ('semicolon', "Semicolon (;)"),
            ('tab', "Tab"),
            ('space', "Space"),
        ],
        string="Separator",
        default='comma',
    )
    text_delimiter = fields.Char(
        string="Text Delimiter",
        default='"',
    )

    @api.constrains('use_header', 'row_num_header', 'row_num_data')
    def _check_row_numbers(self):
        for record in self:
            if record.row_num_data < 1:
                raise ValidationError(_("Data start row number must starts with 1"))

            if record.use_header:
                if record.row_num_header < 1:
                    raise ValidationError(_("Header row number must starts with 1"))
                elif record.row_num_header >= record.row_num_data:
                    raise ValidationError(_("Header and data rows must not intersect"))

                record.line_ids._check_column_name()


class AccountBankStatementImportMappingLine(models.Model):
    _name = 'account.bank.statement.import.mapping.line'
    _description = "Account Bank Statement Import Mapping Line"
    _rec_name = 'bank_statement_line_field'

    mapping_id = fields.Many2one(
        comodel_name='account.bank.statement.import.mapping',
        ondelete='cascade',
        required=True,
    )

    bank_statement_line_field = fields.Selection(
        selection=[
            ('date', "Date"),
            ('partner_id', "Partner"),
            ('partner_name', "Partner Name"),
            ('account_number', "Partner Acc Number"),
            ('amount', "Amount"),
            ('payment_ref', "Label"),
            ('ref', "Reference"),
            ('unique_import_id', "Import ID"),
        ],
        string="Bank Statement Line Field",
        required=True,
    )

    column_name = fields.Char(
        string="Column Name/Number",
        help="Column name (if headers used) or number (starting from 1). Required if Python not used.",
    )

    value_format = fields.Char(
        string="Format",
        default='%d.%m.%Y',
    )
    use_python = fields.Boolean(
        string="Use Python",
        default=False,
    )
    python_code = fields.Text(
        string="Python Code",
        help="""
Code on python used to evaluate value.

Available variables:
field_name - Name of the field to evaluate value
value - value of the column (if column name/index defined); can be None
mapping - current mapping record
mapping_line - current mapping line record
data - whole data set
data_row - current data row as a dictionary with header name as a key or list of values if header not used

For multiline python scripts us local variable named 'result' to return result of code evaluation.
""",
    )

    @api.constrains('bank_statement_line_field')
    def _check_bank_statement_line_field(self):
        for record in self:
            if record.mapping_id.line_ids.filtered(lambda r: r != record and r.bank_statement_line_field == record.bank_statement_line_field):
                raise ValidationError(_("Bank statement line field must be used once per mapping"))

    @api.constrains('column_name')
    def _check_column_name(self):
        for record in self:
            if record.column_name:
                if not record.mapping_id.use_header:
                    try:
                        column_number = int(record.column_name)
                    except:
                        raise ValidationError(_("If header not used, line must be mapped by column number (starts with 1)"))

                    if column_number < 1:
                        raise ValidationError(_("Column number must starts with 1"))
            else:
                if not record.use_python:
                    raise ValidationError(_("Column Name/Number is required"))

    @api.constrains('python_code')
    def _check_python_code(self):
        for record in self:
            if record.use_python and (not record.python_code or not record.python_code.strip()):
                raise ValidationError(_("Python code is required"))

    @api.onchange('use_python')
    def _onchange_use_python(self):
        for record in self:
            if not record.use_python:
                record.python_code = None
