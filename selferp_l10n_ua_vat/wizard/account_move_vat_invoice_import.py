import logging

from datetime import datetime
from io import BytesIO
from lxml import etree
from zipfile import ZipFile

from odoo import api, models, fields, Command, _
from odoo.exceptions import UserError
from odoo.tools import config


VAT_CODE_TAGS = {
    'vendor_vat_invoice': {
        '20': 'R01G7',
        '7': 'R01G109',
        '14': 'R01G14',
        '901': 'R01G9',
        '902': 'R01G8',
        '903': 'R01G10',
    },
    'vendor_vat_adjustment_invoice': {
        '20': 'R01G9',
        '7': 'R01G111',
        '14': 'R01G14',
        '901': 'R006G03',
        '902': 'R007G03',
        '903': 'R01G11',
    },
}


_logger = logging.getLogger(__name__)


def _parse_text(root, xpath, strip=True):
    value = root.findtext(xpath) or ''
    if value and strip:
        value = value.strip()
    return value


def _parse_date(root, xpath):
    value = _parse_text(root, xpath, strip=True)
    if value:
        return datetime.strptime(value, '%d%m%Y').date()
    return None


def _parse_boolean(root, xpath):
    return _parse_text(root, xpath, strip=True) and True or False


def _parse_float(root, xpath, always_zero=True):
    value = _parse_text(root, xpath, strip=True)
    if value:
        return float(value)
    return 0.0 if always_zero else None


class AccountMoveVATInvoiceImportWizard(models.TransientModel):
    _name = 'account.move.vat_invoice.import'
    _description = "Import VAT invoice wizard"

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Add files for import",
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count',
    )

    @api.depends('attachment_ids')
    @api.onchange('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    def action_confirm(self):
        self.ensure_one()

        if not self.attachment_ids:
            raise UserError(_("Select at least one file for import, please."))

        # import records
        records = self.env['account.move'].browse()

        for file in self.attachment_ids:
            if file.mimetype == 'application/zip':
                records += self._import_zip(file.name, file.raw)
            else:
                records += self._import_xml(file.name, file.raw)

        # open imported records
        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('selferp_l10n_ua_vat.account_move_action_vendor_vat_invoice')
        if len(records) == 1:
            action.update({
                'res_id': records.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'view_id': None,
            })
        else:
            action['domain'] = [('id', 'in', records.ids)]

        return action

    def _import_zip(self, file_name, file_data):
        records = self.env['account.move'].browse()

        with ZipFile(BytesIO(file_data)) as file_zip:
            for name in file_zip.namelist():
                data = file_zip.read(name)
                records += self._import_xml(name, data)

        return records

    def _import_xml(self, file_name, file_data):
        try:
            # parse XML
            xml_root = etree.fromstring(file_data)

            # find and check company
            company_vat = _parse_text(xml_root, 'DECLARBODY/HKBUY')
            company = self.env['res.company'].search([
                ('partner_id.vat', '=', company_vat),
            ])
            if not company:
                raise UserError(_("Company not found by VAT '%(company_vat)s'!", company_vat=company_vat))
            if len(company) > 1:
                raise UserError(_("More than one company found by VAT '%(company_vat)s'!", company_vat=company_vat))

            # find and check partner
            partner_vat = _parse_text(xml_root, 'DECLARBODY/HKSEL')
            partner = self.env['res.partner'].search([
                ('vat', '=', partner_vat),
            ])

            if not partner:
                raise UserError(_("Vendor not found by VAT '%(partner_vat)s'!", partner_vat=partner_vat))
            if len(partner) > 1:
                raise UserError(_("More than one vendor found by VAT '%(partner_vat)s'!", partner_vat=partner_vat))

            # get type and date
            invoice_type = 'vendor_vat_adjustment_invoice' if _parse_text(xml_root, 'DECLARHEAD/C_DOC_SUB') == '012' else 'vendor_vat_invoice'
            external_number = _parse_text(xml_root, 'DECLARBODY/HNUM')
            invoice_date = _parse_date(xml_root, 'DECLARBODY/HFILL')

            # check existing
            AccountMove = self.env['account.move'].with_company(company)
            if AccountMove.search_count([
                ('company_id', '=', company.id),
                ('move_type', '=', invoice_type),
                ('partner_id', '=', partner.id),
                ('external_number', '=', external_number),
                ('issuance_date', '=', invoice_date),
            ]):
                raise UserError(_(
                    "%(partner_name)s, %(issuance_date)s, %(external_number)s Vendor Vat Invoice already exists in the database",
                    partner_name=partner.name,
                    issuance_date=fields.Date.to_string(invoice_date),
                    external_number=external_number,
                ))

            values = {
                'company_id': company.id,
                'move_type': invoice_type,
                'partner_id': partner.id,
                'external_number': external_number,
                'issuance_date': invoice_date,
                'date': invoice_date,
                'to_vat_invoice_exempt_from_taxation': _parse_boolean(xml_root, 'DECLARBODY/R03G10S'),
            }

            # try to find Vendor VAT Invoice (if you need)
            if invoice_type == 'vendor_vat_adjustment_invoice':
                source_external_number = _parse_text(xml_root, 'DECLARBODY/HPODNUM')
                source_issuance_date = _parse_date(xml_root, 'DECLARBODY/HPODFILL')

                if source_external_number and source_issuance_date:
                    vendor_vat_invoice = AccountMove.search(
                        [
                            ('company_id', '=', company.id),
                            ('move_type', '=', 'vendor_vat_invoice'),
                            ('external_number', '=', source_external_number),
                            ('issuance_date', '=', source_issuance_date),
                        ],
                        limit=1,
                    )

                    if vendor_vat_invoice:
                        values['vendor_vat_invoice_id'] = vendor_vat_invoice.id

            # add lines
            vat_lines = []
            AccountTax = self.env['account.tax'].with_company(company)

            for vat_code, tag_name in VAT_CODE_TAGS[invoice_type].items():
                value = _parse_float(xml_root, f'DECLARBODY/{tag_name}')

                if value:
                    tax = AccountTax.search(
                        [
                            ('company_id', '=', company.id),
                            ('type_tax_use', '=', 'purchase'),
                            ('price_include', '!=', True),
                            ('tax_group_id.is_vat', '=', True),
                            ('tax_group_id.vat_code', '=', vat_code),
                        ],
                        limit=1,
                    )

                    if not tax:
                        raise UserError(_("Tax with code %s not found", vat_code))

                    vat_lines.append(Command.create({
                        'vat_tax_id': tax.id,
                        'total_without_vat': value,
                    }))

            if vat_lines:
                values['vat_line_ids'] = vat_lines

            # create invoice
            return AccountMove.create(values)

        except Exception as e:
            if not config['test_enable']:
                _logger.error("VAT Invoice import error", exc_info=e)
            raise UserError(_(
                "VAT Invoice import error [%(file_name)s]: %(error_message)s",
                file_name=file_name,
                error_message=e,
            ))

