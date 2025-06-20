import re

from collections import defaultdict, OrderedDict

from odoo import api, models, fields, _

from odoo.addons.selferp_l10n_ua_ext.models.account_editable_report import round_amount, sum_amount, sum_all_by_keys, put_doc_values, extract_doc_values, check_not_empty_doc
from odoo.addons.selferp_l10n_ua_ext.utils.export_xml import export_xml_create_base_head, export_xml_file_name


DOC_DECLARATION = 'J0200125'    # Декларація
DOC_APPENDIX_1 = 'J0200525'     # Додаток 1
DOC_APPENDIX_2 = 'J0215225'     # Додаток 2
DOC_APPENDIX_3 = 'J0200625'     # Додаток 3
DOC_APPENDIX_4 = 'J0299825'     # Додаток 4
DOC_APPENDIX_5 = 'J0299325'     # Додаток 5
DOC_APPENDIX_6 = 'J0215725'     # Додаток 6
DOC_APPENDIX_7 = 'J0215825'     # Додаток 7

DOCS = tuple([
    DOC_DECLARATION,
    DOC_APPENDIX_1,
    DOC_APPENDIX_2,
    DOC_APPENDIX_3,
    DOC_APPENDIX_4,
    DOC_APPENDIX_5,
    DOC_APPENDIX_6,
    DOC_APPENDIX_7,
])


def _lines_by_tax_group(env, records):
    result = defaultdict(env['account.move.vat.line'].browse)

    if records:
        if records._name == 'account.move':
            records = records.mapped('vat_line_ids')

        for line in records:
            vat_code = line.vat_tax_id.tax_group_id and line.vat_tax_id.tax_group_id.vat_code or None
            result[vat_code] += line

    return result


class AccountVATTaxReport(models.Model):
    _name = 'account.vat.tax_report'
    _inherit = 'account.editable.report'
    _description = "VAT Tax Report"
    _order = 'date_from DESC, date_to DESC, id DESC'

    rendered_html_part_J0200125 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0200525 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0215225 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0200625 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0299825 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0299325 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0215725 = fields.Html(
        compute='_compute_rendered_html_parts',
    )
    rendered_html_part_J0215825 = fields.Html(
        compute='_compute_rendered_html_parts',
    )

    include_J0200525 = fields.Boolean(default=False)
    include_J0215225 = fields.Boolean(default=False)
    include_J0200625 = fields.Boolean(default=False)
    include_J0299825 = fields.Boolean(default=False)
    include_J0299325 = fields.Boolean(default=False)
    include_J0215725 = fields.Boolean(default=False)
    include_J0215825 = fields.Boolean(default=False)

    @api.model
    def _get_editable_report_sequence(self, vals):
        company_id = vals.get('company_id')
        if company_id:
            company = self.env['res.company'].browse(company_id) or self.env.company
        if company.sequence_vat_tax_report_id:
            return company.sequence_vat_tax_report_id
        else:
            return None     # should never happen

    @api.model
    def _get_part_names(self):
        return DOCS

    @api.model
    def _get_part_title(self, part_name):
        title = _("ПОДАТКОВА ДЕКЛАРАЦІЯ З ПОДАТКУ НА ДОДАНУ ВАРТІСТЬ")
        if part_name == DOC_APPENDIX_1:
            title += ' - ' + _("Appendix 1")
        elif part_name == DOC_APPENDIX_2:
            title += ' - ' + _("Appendix 2")
        elif part_name == DOC_APPENDIX_3:
            title += ' - ' + _("Appendix 3")
        elif part_name == DOC_APPENDIX_4:
            title += ' - ' + _("Appendix 4")
        elif part_name == DOC_APPENDIX_5:
            title += ' - ' + _("Appendix 5")
        elif part_name == DOC_APPENDIX_6:
            title += ' - ' + _("Appendix 6")
        elif part_name == DOC_APPENDIX_7:
            title += ' - ' + _("Appendix 7")
        return title

    @api.model
    def _get_part_action_name(self, part_name):
        return f'selferp_l10n_ua_vat.account_vat_tax_report_action_{part_name}'

    @api.model
    def _get_part_report_name(self, part_name):
        return f'selferp_l10n_ua_vat.account_vat_tax_report_template_content_{part_name}'

    # -------------------------------------------------------------------------
    # GENERATE INITIAL DATA
    # -------------------------------------------------------------------------

    def _generate_data(self):
        self.ensure_one()

        # define params
        self.date_generate = fields.Datetime.now()

        values = {
            'HZ': 'HZ',

            'HZY': self.date_from.strftime('%Y'),
            'HZM': self.date_from.strftime('%m'),

            'HNAME': self.company_id.name,
            'HDDVG': '',
            'HNDVG': '',
            'HTIN': self.company_id.company_registry,
            'HNPDV': self.company_id.vat,

            'HLOC': ', '.join([
                a.strip()
                for a in (self.company_id.partner_id._display_address(without_company=True) or '').split('\n')
                if a.strip()
            ]),
            'HZIP': self.company_id.zip or '',
            'HTEL': self.company_id.phone or '',
            'HEMAIL': self.company_id.email or '',

            'HSTI': self.company_id.tax_inspection_id and self.company_id.tax_inspection_id.name or '',

            'HFILL': self.date_generate.strftime('%d.%m.%Y'),
            'HBOS': self.company_id.director_id and self.company_id.director_id.name or '',
            'HKBOS': self.company_id.director_id and self.company_id.director_id.vat or '',
            'HBUH': self.company_id.chief_accountant_id and self.company_id.chief_accountant_id.name or '',
            'HKBUH': self.company_id.chief_accountant_id and self.company_id.chief_accountant_id.vat or '',
        }

        # fill all documents
        for doc_key in DOCS:
            method_name = f'_generate_data_{doc_key}'
            if hasattr(self, method_name):
                # get doc values
                doc_values = getattr(self, method_name)(values)

                # prepare values and put into complete values
                put_doc_values(values, doc_key, doc_values)

        # return generated data
        return values

    def _generate_data_J0200125(self, values):
        """ Generate DECLARATION document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()
        country_ua = self.env.ref('base.ua')

        doc_values = {
            'HA': '',           # manual
            'HK': '',           # manual
            'HD1': '',          # auto-computed
            'HD2': '',          # auto-computed
            'HD3': '',          # auto-computed
            'HD4': '',          # auto-computed
            'HD5': '',          # auto-computed
            'HD6': '',          # auto-computed
            'HD7': '',          # auto-computed
            'HD2P': '',         # manual
            'HVMD': '',         # manual
            'HJAR': '',         # manual (@TODO: maybe auto-computed depending on T1RXXXX?)

            'T1RXXXX': [],      # manual
            'T2RXXXX': [],      # manual
        }

        #
        # ПОДАТКОВІ ЗОБОВ'ЯЗАННЯ
        #
        vat_lines = self.env['account.move.vat.line'].search([
            ('move_id.company_id', '=', self.company_id.id),
            ('move_id.move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
            ('move_id.state', '=', 'posted'),
            ('move_id.vat_invoice_stage', '!=', 'cancelled'),
            ('move_id.date', '>=', self.date_from),
            ('move_id.date', '<=', self.date_to),
        ])
        grouped_vat_lines = _lines_by_tax_group(self.env, vat_lines.filtered(lambda r: r.move_id.move_type == 'vat_invoice'))
        grouped_vat_lines_adj = _lines_by_tax_group(self.env, vat_lines.filtered(lambda r: r.move_id.move_type == 'vat_adjustment_invoice'))

        # Рядок 1: Операції на митній території України, що оподатковуються
        # за основною ставкою та ставками 7 % і 14 %, крім ввезення товарів
        # на митну територію України
        def _filter_r1(r):
            return (
                not (r.move_id.consolidated_vat_invoice and r.move_id.consolidated_tax_code in ('1', '2'))
                and not (r.move_id.not_issued_to_customer and r.move_id.reason_type == '14')
            )

        _r1_vat_lines_20 = grouped_vat_lines['20'].filtered(_filter_r1)
        _r1_vat_lines_7 = grouped_vat_lines['7'].filtered(_filter_r1)
        _r1_vat_lines_14 = grouped_vat_lines['14'].filtered(_filter_r1)

        doc_values.update({
            'R11GA': sum_amount(_r1_vat_lines_20, 'total_without_vat'),
            'R11GB': sum_amount(_r1_vat_lines_20, 'vat_amount'),
            'R12GA': sum_amount(_r1_vat_lines_7, 'total_without_vat'),
            'R12GB': sum_amount(_r1_vat_lines_7, 'vat_amount'),
            'R13GA': sum_amount(_r1_vat_lines_14, 'total_without_vat'),
            'R13GB': sum_amount(_r1_vat_lines_14, 'vat_amount'),

            'R21GA': sum_amount(grouped_vat_lines['901'].filtered(lambda r: r.move_id.reason_type == '07'), 'total_without_vat'),
            'R22GA': sum_amount(grouped_vat_lines['903'].filtered(lambda r: r.move_id.partner_id.country_id and r.move_id.partner_id.country_id != country_ua), 'total_without_vat'),
            'R30GA': sum_amount(grouped_vat_lines['902'] + grouped_vat_lines_adj['902'], 'total_without_vat'),
        })

        # Рядок 4: Нараховано податкових зобов'язань відповідно до пункту 198.5
        # статті 198 та пункту 199.1 статті 199 розділу V Податкового кодексу України
        def _filter_r4(r):
            return r.move_id.consolidated_vat_invoice and r.move_id.consolidated_tax_code in ('1', '2')

        def _filter_r4_adj(r):
            return (
                r.move_id.vat_invoice_adjustment_id
                and r.move_id.vat_invoice_adjustment_id.consolidated_vat_invoice
                and r.move_id.vat_invoice_adjustment_id.consolidated_tax_code in ('1', '2')
            )

        _r4_vat_lines_20 = grouped_vat_lines['20'].filtered(_filter_r4)
        _r4_vat_lines_20_adj = grouped_vat_lines_adj['20'].filtered(_filter_r4_adj)
        _r4_vat_lines_7 = grouped_vat_lines['7'].filtered(_filter_r4)
        _r4_vat_lines_7_adj = grouped_vat_lines_adj['7'].filtered(_filter_r4_adj)
        _r4_vat_lines_14 = grouped_vat_lines['14'].filtered(_filter_r4)
        _r4_vat_lines_14_adj = grouped_vat_lines_adj['14'].filtered(_filter_r4_adj)

        doc_values.update({
            'R41GA': sum_amount(_r4_vat_lines_20, 'total_without_vat'),
            'R41GB': sum_amount(_r4_vat_lines_20, 'vat_amount'),
            'R411GA': sum_amount(_r4_vat_lines_20_adj, 'total_without_vat'),
            'R411GB': sum_amount(_r4_vat_lines_20_adj, 'vat_amount'),

            'R42GA': sum_amount(_r4_vat_lines_7, 'total_without_vat'),
            'R42GB': sum_amount(_r4_vat_lines_7, 'vat_amount'),
            'R421GA': sum_amount(_r4_vat_lines_7_adj, 'total_without_vat'),
            'R421GB': sum_amount(_r4_vat_lines_7_adj, 'vat_amount'),

            'R43GA': sum_amount(_r4_vat_lines_14, 'total_without_vat'),
            'R43GB': sum_amount(_r4_vat_lines_14, 'vat_amount'),
            'R431GA': sum_amount(_r4_vat_lines_14_adj, 'total_without_vat'),
            'R431GB': sum_amount(_r4_vat_lines_14_adj, 'vat_amount'),
        })

        # Рядок 5: Операції, що не є об'єктом оподаткування, операції з постачання
        # послуг за межами митної території України та послуг, місце постачання
        # яких визначено відповідно до пунктів 186.2, 186.3 статті 186 розділу V
        # Кодексу за межами митної території України, операції, які звільнені від
        # оподаткування
        _r5_vat_lines_903 = grouped_vat_lines['903'].filtered(lambda r: not r.move_id.partner_id.country_id or r.move_id.partner_id.country_id == country_ua)
        _r5_vat_lines_903_adj = grouped_vat_lines_adj['903'].filtered(lambda r: not r.move_id.partner_id.country_id or r.move_id.partner_id.country_id == country_ua)
        doc_values.update({
            'R50GA': 0,     # auto-computed (= R01G4 + R02G5 of APPENDIX 5)

            # 'R51GA': _sum_amount(_r5_vat_lines_903, 'total_without_vat'),
            'R51GA': 0,     # auto-computed (= R02G5 of APPENDIX 5)

            'R511GA': sum_amount(_r5_vat_lines_903_adj, 'total_without_vat'),
        })

        # Рядок 6: Послуги, отримані від нерезидента, місце постачання яких
        # визначено на митній території України
        _r6_vat_lines_20 = (grouped_vat_lines['20'] + grouped_vat_lines_adj['20']).filtered(
            lambda r: r.move_id.not_issued_to_customer and r.move_id.reason_type == '14'
        )
        _r6_vat_lines_7 = (grouped_vat_lines['7'] + grouped_vat_lines_adj['7']).filtered(
            lambda r: r.move_id.not_issued_to_customer and r.move_id.reason_type == '14'
        )

        doc_values.update({
            'R61GA': sum_amount(_r6_vat_lines_20, 'total_without_vat'),
            'R61GB': sum_amount(_r6_vat_lines_20, 'vat_amount'),
            'R62GA': sum_amount(_r6_vat_lines_7, 'total_without_vat'),
            'R62GB': sum_amount(_r6_vat_lines_7, 'vat_amount'),
        })

        # Рядок 7: Коригування податкових зобов'язань
        #
        # всі Розрахунки-коригування до податкових накладних зі ставками
        # 20%, 7%, 14% за виключенням тих, які включені у R411GA, R411GB,
        # R421GA, R421GB, R431GA, R511GA та тих які зі знаком "-" у статусі
        # "Зареєстровано".
        # Окрім РК з типом причини невидачі 14 (R61GA, R61GB, R62GA, R62GB)
        _r7_vat_lines = (vat_lines - _r4_vat_lines_20_adj - _r4_vat_lines_7_adj - _r4_vat_lines_14_adj - _r5_vat_lines_903_adj).filtered(
            lambda r: r.move_id.move_type == 'vat_adjustment_invoice'
                      and not (r.move_id.vat_line_tax < 0 and r.move_id.vat_invoice_stage in ('prepared', 'on_registration', 'blocked'))
                      and not (r.move_id.not_issued_to_customer and r.move_id.reason_type == '14')
        )

        doc_values.update({
            'R70GA': sum_amount(_r7_vat_lines, 'total_without_vat'),
            'R70GB': sum_amount(_r7_vat_lines, 'vat_amount'),
        })

        # add total
        doc_values.update({
            'R80GA': 0,     # manually
            'R80GB': 0,     # manually

            'R90GB': 0,     # auto-computed
        })

        #
        # ПОДАТКОВИЙ КРЕДИТ
        #
        vat_lines = self.env['account.move.vat.line'].search([
            ('move_id.company_id', '=', self.company_id.id),
            ('move_id.move_type', '=', 'vendor_vat_invoice'),                   # without 'vendor_vat_adjustment_invoice'
            ('move_id.state', '=', 'posted'),
            ('move_id.vat_invoice_stage', '!=', 'cancelled'),
            ('move_id.date', '>=', self.date_from),
            ('move_id.date', '<=', self.date_to),
        ])
        vat_lines_not_import = vat_lines.filtered(lambda r: not r.move_id.is_import)
        vat_lines_import = vat_lines - vat_lines_not_import

        grouped_vat_lines_not_import = _lines_by_tax_group(self.env, vat_lines_not_import)
        grouped_vat_lines_import = _lines_by_tax_group(self.env, vat_lines_import)

        doc_values.update({
            'R101GA': sum_amount(grouped_vat_lines_not_import['20'], 'total_without_vat'),
            'R101GB': sum_amount(grouped_vat_lines_not_import['20'], 'vat_amount'),
            'R102GA': sum_amount(grouped_vat_lines_not_import['7'], 'total_without_vat'),
            'R102GB': sum_amount(grouped_vat_lines_not_import['7'], 'vat_amount'),
            'R103GA': sum_amount(grouped_vat_lines_not_import['14'], 'total_without_vat'),
            'R103GB': sum_amount(grouped_vat_lines_not_import['14'], 'vat_amount'),

            'R104GA': 0,    # manual

            'R111GA': sum_amount(grouped_vat_lines_import['20'], 'total_without_vat'),
            'R111GB': sum_amount(grouped_vat_lines_import['20'], 'vat_amount'),
            'R112GA': sum_amount(grouped_vat_lines_import['7'], 'total_without_vat'),
            'R112GB': sum_amount(grouped_vat_lines_import['7'], 'vat_amount'),
            'R113GA': sum_amount(grouped_vat_lines_import['14'], 'total_without_vat'),
            'R113GB': sum_amount(grouped_vat_lines_import['14'], 'vat_amount'),

            'R120GA': 0,    # manual
            'R120GB': 0,    # manual

            'R131GA': 0,    # auto-computed (= R0223G4 of APPENDIX 1)
            'R131GB': 0,    # auto-computed (= R0223G5 of APPENDIX 1)
            'R132GA': 0,    # auto-computed (= R0224G4 of APPENDIX 1)
            'R132GB': 0,    # auto-computed (= R0224G6 of APPENDIX 1)

            'R140GA': 0,    # auto-computed (= R022G4 of APPENDIX 1)
            'R140GB': 0,    # auto-computed (= R022G5 + R022G6 + R022G7 of APPENDIX 1)

            'R150GA': 0,    # manual
            'R150GB': 0,    # manual

            'R160GB': 0,    # manual
            'R161GB': 0,    # manual
            'R162GB': 0,    # manual
            'R163GB': 0,    # manual

            'R170GB': 0,    # auto-computed
            'R180GB': 0,    # auto-computed
            'R190GB': 0,    # auto-computed
            'R191GB': 0,    # auto-computed
            'R191G3': 0,    # manual

            'R200GB': 0,    # auto-computed
            'R201GB': 0,    # manual
            'R202GB': 0,    # auto-computed
            'R2021GB': 0,   # manual
            'R2022GB': 0,   # auto-computed
            'R203GB': 0,    # auto-computed
            'R210GB': 0,    # auto-computed
        })

        # return doc values
        return doc_values

    def _generate_data_J0200525(self, values):
        """ Generate APPENDIX 1 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        #
        # Розділ І. Податкові зобов'язання
        #
        vat_invoices = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
            ('state', '=', 'posted'),
            ('vat_invoice_stage', 'in', ('on_registration', 'blocked')),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ], order='name')

        def _fill_table(records, table_name):
            _table = []

            for record in records:
                grouped = _lines_by_tax_group(self.env, record.vat_line_ids)

                g7 = sum_amount(grouped['20'], 'vat_amount')
                g8 = sum_amount(grouped['7'], 'vat_amount')
                g9 = sum_amount(grouped['14'], 'vat_amount')

                if g7 or g8 or g9:
                    _table.append({
                        table_name + 'G2': record.partner_id.vat or '',
                        table_name + 'G3D': record.date.strftime('%d.%m.%Y'),
                        table_name + 'G4S': int(re.findall(r'(\d+)$', record.name)[-1]),
                        table_name + 'G5': '+' if record.consolidated_vat_invoice and record.consolidated_tax_code in ('1', '2') else '',
                        table_name + 'G6': sum_amount(grouped['20'] + grouped['7'] + grouped['14'], 'total_without_vat'),
                        table_name + 'G7': g7,
                        table_name + 'G8': g8,
                        table_name + 'G9': g9,
                    })

            return _table

        doc_values = {
            'T111RXXXX': _fill_table(
                vat_invoices.filtered(lambda r: r.move_type == 'vat_invoice' and not (r.not_issued_to_customer and r.reason_type == '14')),
                'T111RXXXX',
            ),
            'R0111G6': 0,       # auto-computed
            'R0111G7': 0,       # auto-computed
            'R0111G8': 0,       # auto-computed
            'R0111G9': 0,       # auto-computed

            'T112RXXXX': _fill_table(
                vat_invoices.filtered(lambda r: r.move_type == 'vat_invoice' and r.not_issued_to_customer and r.reason_type == '14'),
                'T112RXXXX',
            ),
            'R0112G6': 0,       # auto-computed
            'R0112G7': 0,       # auto-computed
            'R0112G8': 0,       # auto-computed

            'T121RXXXX': _fill_table(
                # @TODO: filter positive (+) only
                vat_invoices.filtered(lambda r: r.move_type == 'vat_adjustment_invoice' and not (r.not_issued_to_customer and r.reason_type == '14')),
                'T121RXXXX',
            ),
            'R0121G6': 0,       # auto-computed
            'R0121G7': 0,       # auto-computed
            'R0121G8': 0,       # auto-computed
            'R0121G9': 0,       # auto-computed

            'T123RXXXX': _fill_table(
                # @TODO: filter positive (+) only
                vat_invoices.filtered(lambda r: r.move_type == 'vat_invoice' and r.not_issued_to_customer and r.reason_type == '14'),
                'T123RXXXX',
            ),
            'R0123G6': 0,       # auto-computed
            'R0123G7': 0,       # auto-computed
            'R0123G8': 0,       # auto-computed

            'T124RXXXX': [],    # manual
            'R0124G6': 0,       # auto-computed
            'R0124G7': 0,       # auto-computed
            'R0124G8': 0,       # auto-computed
            'R0124G9': 0,       # auto-computed
        }

        #
        # Розділ ІІ. Податковий кредит
        #
        def _group_key(record, with_cash_method):
            _key = [
                record.partner_id.vat or '',
                record.issuance_date.strftime('%m') if record.issuance_date else '',
                record.issuance_date.strftime('%Y') if record.issuance_date else '',
                '+' if record.acquisition_non_current_assets else '',
            ]

            if with_cash_method:
                _key.insert(3, '+' if record.cash_method else '')

            return tuple(_key)

        def _group(records, with_cash_method):
            _groups = {}

            for record in records:
                _key = _group_key(record, with_cash_method)
                _group_values = _groups.get(_key)
                if not _group_values:
                    _group_values = {
                        'total': 0,
                        '20': 0,
                        '7': 0,
                        '14': 0,
                    }
                    _groups[_key] = _group_values

                _lines_grouped = _lines_by_tax_group(self.env, record.vat_line_ids)

                _group_values['total'] += sum_amount(_lines_grouped['20'] + _lines_grouped['7'] + _lines_grouped['14'], 'total_without_vat')
                _group_values['20'] += sum_amount(_lines_grouped['20'], 'vat_amount')
                _group_values['7'] += sum_amount(_lines_grouped['7'], 'vat_amount')
                _group_values['14'] += sum_amount(_lines_grouped['14'], 'vat_amount')

            return _groups

        vendor_vat_invoices = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ('vendor_vat_invoice', 'vendor_vat_adjustment_invoice')),
            ('state', '=', 'posted'),
            ('vat_invoice_stage', '!=', 'cancelled'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('is_import', '=', False),
        ])

        #
        # Таблиця 2.1. Відомості про операції з придбання з податком на додану
        # вартість, які підлягають оподаткуванню за основною ставкою та ставками 7% і 14%
        #
        vendor_vat_invoices_grouped = _group(vendor_vat_invoices.filtered(lambda r: r.move_type == 'vendor_vat_invoice'), True)
        if len(vendor_vat_invoices_grouped) > 1:
            vendor_vat_invoices_grouped = OrderedDict(sorted(vendor_vat_invoices_grouped.items()))

        _T21RXXXX = []
        for group_key, group_values in vendor_vat_invoices_grouped.items():
            _T21RXXXX.append({
                'T21RXXXXG2': group_key[0],
                'T21RXXXXG31': group_key[1],
                'T21RXXXXG32': group_key[2],
                'T21RXXXXG4': group_key[3],
                'T21RXXXXG5': group_key[4],
                'T21RXXXXG6': group_values['total'],
                'T21RXXXXG7': group_values['20'],
                'T21RXXXXG8': group_values['7'],
                'T21RXXXXG9': group_values['14'],
            })
        doc_values.update({
            'T21RXXXX': _T21RXXXX,

            'R021G6': 0,        # auto-computed
            'R021G7': 0,        # auto-computed
            'R021G8': 0,        # auto-computed
            'R021G9': 0,        # auto-computed
            'R0211G6': 0,       # auto-computed
            'R0211G7': 0,       # auto-computed
            'R0211G8': 0,       # auto-computed
            'R0212G6': 0,       # auto-computed
            'R0212G7': 0,       # auto-computed
        })

        #
        # Таблиця 2.2. Відомості про коригування податкового кредиту згідно зі
        # ст. 192 розділу V Кодексу
        #
        vendor_vat_adjustment_invoices_grouped = _group(vendor_vat_invoices.filtered(lambda r: r.move_type == 'vendor_vat_adjustment_invoice'), False)
        if len(vendor_vat_adjustment_invoices_grouped) > 1:
            vendor_vat_adjustment_invoices_grouped = OrderedDict(sorted(vendor_vat_adjustment_invoices_grouped.items()))

        _T22RXXXX = []
        for group_key, group_values in vendor_vat_adjustment_invoices_grouped.items():
            _T22RXXXX.append({
                'T22RXXXXG2': group_key[0],
                'T22RXXXXG311': group_key[1],
                'T22RXXXXG312': group_key[2],
                'T22RXXXXG32': group_key[3],
                'T22RXXXXG4': group_values['total'],
                'T22RXXXXG5': group_values['20'],
                'T22RXXXXG6': group_values['7'],
                'T22RXXXXG7': group_values['14'],
            })
        doc_values.update({
            'T22RXXXX': _T22RXXXX,

            'R022G4': 0,        # auto-computed
            'R022G5': 0,        # auto-computed
            'R022G6': 0,        # auto-computed
            'R022G7': 0,        # auto-computed
            'R0221G4': 0,       # auto-computed
            'R0221G5': 0,       # auto-computed
            'R0221G6': 0,       # auto-computed
            'R0223G4': 0,       # manual
            'R0223G5': 0,       # manual
            'R0224G4': 0,       # manual
            'R0224G6': 0,       # manual
        })

        # return doc values
        return doc_values

    def _generate_data_J0215225(self, values):
        """ Generate APPENDIX 2 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()
        doc_values = {}

        doc_values = {
            'T1RXXXX': [],      # manual
            'R01G5': 0,         # manual
            'R02G5': 0,         # auto-computed
            'R02G6': 0,         # auto-computed

            'R03G2': '',        # manual

            'T2RXXXX': [],      # manual
            'R04G3': 0,         # auto-computed

            'T3RXXXX': [],      # manual
            'R05G5': 0,         # auto-computed
        }

        # return doc values
        return doc_values

    def _generate_data_J0200625(self, values):
        """ Generate APPENDIX 3 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        doc_values = {
            'R010G3': 0,        # manual
            'R020G3': 0,        # manual
            'R030G3': 0,        # manual

            'T1RXXXX': [],      # manual
            'R01G5': 0,         # auto-computed
            'R01G7': 0,         # auto-computed
        }

        # return doc values
        return doc_values

    def _generate_data_J0299825(self, values):
        """ Generate APPENDIX 4 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        doc_values = {
            'R0303G2': '',      # manual
            'R0303G3': '',      # manual
            'R0304G2': '',      # manual
            'R0305G1S': '',     # manual
            'R0305G3S': '',     # manual

            'R0401G2': '',      # manual
            'R0401G3': '',      # manual
            'R0402G2S': '',     # manual
            'R0403G1S': '',     # manual

            'T1RXXXX': [],      # manual
            'R05G4': 0,         # auto-computed

            'R06G1': '',        # manual
            'R06G2': '',        # manual
            'R06G3': '',        # manual
            'R06G4': '',        # manual

            'R07G1': '',        # manual
            'R07G2S': '',       # manual
            'R07G3S': '',       # manual

            'R07G4': '',        # manual

            'R08G1': '',        # manual

            'T4RXXXX': [],      # manual
            'R09G3': 0,         # auto-computed

            'T5RXXXX': [],      # manual
            'R010G4': 0,        # auto-computed
        }

        # return doc values
        return doc_values

    def _generate_data_J0299325(self, values):
        """ Generate APPENDIX 5 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        doc_values = {
            'T11RXXXX': [],     # manual
            'R011G4': 0,        # auto-computed

            'T12RXXXX': [],     # manual
            'R012G4': 0,        # auto-computed
            'R01G4': 0,         # auto-computed (R011G4 + R012G4)

            'T2RXXXX': [],      # see below
            'R02G4': 0,         # auto-computed
            'R02G5': 0,         # auto-computed
            'R02G6': 0,         # auto-computed
            'R02G7': 0,         # auto-computed
            'R02G8': 0,         # auto-computed
            'R02G9': 0,         # auto-computed

            'R04G2': '',        # manual
            'R05G2': '',        # manual
            'R06G2': '',        # manual
            'R07G2': '',        # manual
            'R08G2': '',        # manual
        }

        # determine table value
        _T2RXXXX = []

        lines = self.env['account.move.vat.line'].search_read(
            domain=[
                ('move_id.company_id', '=', self.company_id.id),
                ('move_id.move_type', '=', 'vat_invoice'),
                ('move_id.state', '=', 'posted'),
                ('move_id.vat_invoice_stage', '!=', 'cancelled'),
                ('move_id.date', '>=', self.date_from),
                ('move_id.date', '<=', self.date_to),
                ('benefit_code_id', '!=', False),
                ('move_id.partner_id.country_id', 'in', (False, self.env.ref('base.ua').id)),
            ],
            fields=['benefit_code_id', 'total_without_vat'],
        )

        if lines:
            lines_grouped = defaultdict(list)
            for line in lines:
                lines_grouped[line['benefit_code_id'][0]].append(line)

            benefit_codes = self.env['account.benefit_code'].browse(lines_grouped.keys())
            benefit_codes = {r.id: r for r in benefit_codes}

            for benefit_code_id, lines in lines_grouped.items():
                benefit_code = benefit_codes[benefit_code_id]

                row = {
                    'T2RXXXXG2S': benefit_code.name,
                    'T2RXXXXG3': benefit_code.code,
                    'T2RXXXXG4': 0,     # auto-computed
                    'T2RXXXXG5': sum_amount(lines, 'total_without_vat'),
                    'T2RXXXXG6': 0,     # manual
                    'T2RXXXXG7': 0,     # manual
                    'T2RXXXXG8': 0,     # manual
                    'T2RXXXXG9': 0,     # manual
                }

                _T2RXXXX.append(row)

            if len(_T2RXXXX) > 1:
                _T2RXXXX = list(sorted(_T2RXXXX, key=lambda r: r['T2RXXXXG3']))

        # set table value
        doc_values['T2RXXXX'] = _T2RXXXX

        # return doc values
        return doc_values

    def _generate_data_J0215725(self, values):
        """ Generate APPENDIX 6 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        doc_values = {
            'R011G4': '',       # manual
            'R011G5': '',       # manual
            'R011G6': '',       # manual
            'R011G7': '',       # manual

            'R012G4': '',       # manual
            'R012G5': '',       # manual
            'R012G6': '',       # manual
            'R012G7': '',       # manual

            'R0131G4': '',      # manual
            'R0131G5': '',      # manual
            'R0131G6': '',      # manual
            'R0131G7': '',      # manual

            'R0132G4': '',      # manual
            'R0132G5': '',      # manual
            'R0132G6': '',      # manual
            'R0132G7': '',      # manual

            'R0133G4': '',      # manual
            'R0133G5': '',      # manual
            'R0133G6': '',      # manual
            'R0133G7': '',      # manual

            'T2RXXXX': [],      # manual
            'R02G6': 0,         # auto-computed
            'R02G7': 0,         # auto-computed
            'R02G8': 0,         # auto-computed
            'R02G9': 0,         # auto-computed
            'R02G10': 0,        # auto-computed
            'R02G11': 0,        # auto-computed

            'R031G3': '',       # manual
            'R031G4': '',       # manual
            'R031G5': '',       # manual
            'R031G6': '',       # manual
            'R031G7': '',       # manual

            'R032G3': '',       # manual
            'R032G4': '',       # manual
            'R032G5': '',       # manual
            'R032G6': '',       # manual
            'R032G7': '',       # manual

            'R033G3': '',       # manual
            'R033G4': '',       # manual
            'R033G5': '',       # manual
            'R033G6': '',       # manual
            'R033G7': '',       # manual

            'R041G1': '',       # manual
            'R041G2': '',       # manual
            'R041G3': '',       # manual
            'R041G4': '',       # manual
            'R041G5': '',       # manual
            'R041G6': '',       # manual
            'R041G7': '',       # manual
            'R041G8': '',       # manual
            'R041G9': '',       # manual
            'R041G10': '',      # manual
            'R041G11': '',      # manual
            'R041G12': '',      # manual
            'R041G13': '',      # manual
            'R041G14': '',      # manual
        }

        # return doc values
        return doc_values

    def _generate_data_J0215825(self, values):
        """ Generate APPENDIX 7 document values

        :param values: existing values
        :return: document values
        """
        self.ensure_one()

        doc_values = {
            'T1RXXXX': [],      # manual

            'HEXPL': '',        # manual
        }

        # return doc values
        return doc_values

    # -------------------------------------------------------------------------
    # RECOMPUTE AUTO-COMPUTED VALUES
    # (on each values changes)
    # -------------------------------------------------------------------------

    @api.model
    def _recompute_values(self, values):
        if values:
            # recompute all documents (in reverse order)
            for doc_key in reversed(DOCS):
                method_name = f'_recompute_values_{doc_key}'
                if hasattr(self, method_name):
                    # extract current document values
                    doc_values = extract_doc_values(values, doc_key)

                    # recompute doc values
                    doc_values = getattr(self, method_name)(values, doc_values)

                    # prepare values and put into complete values
                    put_doc_values(values, doc_key, doc_values)

        return values

    @api.model
    def _recompute_values_J0200125(self, all_values, doc_values):
        """ Recompute auto-computed values for DECLARATION

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R50GA': sum_all_by_keys(all_values, ['R01G4', 'R02G5'], DOC_APPENDIX_5),
            'R51GA': sum_all_by_keys(all_values, ['R02G5'], DOC_APPENDIX_5),

            'R90GB': sum_all_by_keys(doc_values, ['R11GB', 'R12GB', 'R13GB', 'R41GB', 'R411GB', 'R42GB', 'R421GB', 'R43GB', 'R431GB', 'R61GB', 'R62GB', 'R70GB', 'R80GB']),

            'R131GA': sum_all_by_keys(all_values, ['R0223G4'], DOC_APPENDIX_1),
            'R131GB': sum_all_by_keys(all_values, ['R0223G5'], DOC_APPENDIX_1),
            'R132GA': sum_all_by_keys(all_values, ['R0224G4'], DOC_APPENDIX_1),
            'R132GB': sum_all_by_keys(all_values, ['R0224G6'], DOC_APPENDIX_1),

            'R140GA': sum_all_by_keys(all_values, ['R022G4'], DOC_APPENDIX_1),
            'R140GB': sum_all_by_keys(all_values, ['R022G5', 'R022G6', 'R022G7'], DOC_APPENDIX_1),
        })

        doc_values['R170GB'] = sum_all_by_keys(doc_values, ['R101GB', 'R102GB', 'R103GB', 'R111GB', 'R112GB', 'R113GB', 'R120GB', 'R131GB', 'R132GB', 'R140GB', 'R150GB', 'R160GB'])

        _R90GB_R170GB = (doc_values.get('R90GB') or 0) - (doc_values.get('R170GB') or 0)
        doc_values.update({
            'R180GB': _R90GB_R170GB if _R90GB_R170GB > 0 else 0,
            'R190GB': -_R90GB_R170GB if _R90GB_R170GB < 0 else 0,
        })
        doc_values['R191GB'] = (doc_values.get('R190GB') or 0) - (doc_values.get('R191G3') or 0)

        doc_values.update({
            'R200GB': (doc_values.get('R190GB') or 0) - (doc_values.get('R191GB') or 0),
            'R202GB': doc_values.get('R030G3') or 0,
        })

        doc_values.update({
            'R2022GB': doc_values.get('R202GB') or 0,
            'R203GB': (doc_values.get('R200GB') or 0) - (doc_values.get('R201GB') or 0) - (doc_values.get('R202GB') or 0),
        })

        doc_values.update({
            'R210GB': sum_all_by_keys(doc_values, ['R191GB', 'R203GB']),
        })

        return doc_values

    @api.model
    def _recompute_values_J0200525(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 1

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R0111G6': sum_amount(doc_values.get('T111RXXXX'), 'T111RXXXXG6'),
            'R0111G7': sum_amount(doc_values.get('T111RXXXX'), 'T111RXXXXG7'),
            'R0111G8': sum_amount(doc_values.get('T111RXXXX'), 'T111RXXXXG8'),
            'R0111G9': sum_amount(doc_values.get('T111RXXXX'), 'T111RXXXXG9'),

            'R0112G6': sum_amount(doc_values.get('T112RXXXX'), 'T112RXXXXG6'),
            'R0112G7': sum_amount(doc_values.get('T112RXXXX'), 'T112RXXXXG7'),
            'R0112G8': sum_amount(doc_values.get('T112RXXXX'), 'T112RXXXXG8'),

            'R0121G6': sum_amount(doc_values.get('T121RXXXX'), 'T121RXXXXG6'),
            'R0121G7': sum_amount(doc_values.get('T121RXXXX'), 'T121RXXXXG7'),
            'R0121G8': sum_amount(doc_values.get('T121RXXXX'), 'T121RXXXXG8'),
            'R0121G9': sum_amount(doc_values.get('T121RXXXX'), 'T121RXXXXG9'),

            'R0123G6': sum_amount(doc_values.get('T123RXXXX'), 'T123RXXXXG6'),
            'R0123G7': sum_amount(doc_values.get('T123RXXXX'), 'T123RXXXXG7'),
            'R0123G8': sum_amount(doc_values.get('T123RXXXX'), 'T123RXXXXG8'),

            'R0124G6': sum_amount(doc_values.get('T124RXXXX'), 'T124RXXXXG6'),
            'R0124G7': sum_amount(doc_values.get('T124RXXXX'), 'T124RXXXXG7'),
            'R0124G8': sum_amount(doc_values.get('T124RXXXX'), 'T124RXXXXG8'),
            'R0124G9': sum_amount(doc_values.get('T124RXXXX'), 'T124RXXXXG9'),
        })

        _T21RXXXX = doc_values.get('T21RXXXX') or []
        _T21RXXXXG4_rows = list(filter(lambda r: r.get('T21RXXXXG4'), _T21RXXXX))
        _T21RXXXXG5_rows = list(filter(lambda r: r.get('T21RXXXXG5'), _T21RXXXX))
        doc_values.update({
            'R021G6': sum_amount(_T21RXXXX, 'T21RXXXXG6'),
            'R021G7': sum_amount(_T21RXXXX, 'T21RXXXXG7'),
            'R021G8': sum_amount(_T21RXXXX, 'T21RXXXXG8'),
            'R021G9': sum_amount(_T21RXXXX, 'T21RXXXXG9'),
            'R0211G6': sum_amount(_T21RXXXXG4_rows, 'T21RXXXXG6'),
            'R0211G7': sum_amount(_T21RXXXXG4_rows, 'T21RXXXXG7'),
            'R0211G8': sum_amount(_T21RXXXXG4_rows, 'T21RXXXXG8'),
            'R0212G6': sum_amount(_T21RXXXXG5_rows, 'T21RXXXXG6'),
            'R0212G7': sum_amount(_T21RXXXXG5_rows, 'T21RXXXXG7'),
        })

        _T22RXXXX = doc_values.get('T22RXXXX') or []
        _T22RXXXXG32_rows = list(filter(lambda r: r.get('T22RXXXXG32'), _T22RXXXX))
        doc_values.update({
            'R022G4': sum_amount(_T22RXXXX, 'T22RXXXXG4'),
            'R022G5': sum_amount(_T22RXXXX, 'T22RXXXXG5'),
            'R022G6': sum_amount(_T22RXXXX, 'T22RXXXXG6'),
            'R022G7': sum_amount(_T22RXXXX, 'T22RXXXXG7'),
            'R0221G4': sum_amount(_T22RXXXXG32_rows, 'T22RXXXXG32'),
            'R0221G5': sum_amount(_T22RXXXXG32_rows, 'T22RXXXXG32'),
            'R0221G6': sum_amount(_T22RXXXXG32_rows, 'T22RXXXXG32'),
        })

        return doc_values

    @api.model
    def _recompute_values_J0215225(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 2

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R02G5': sum_amount(doc_values.get('T1RXXXX'), 'T1RXXXXG5') + (doc_values.get('R01G5') or 0),
            'R02G6': sum_amount(doc_values.get('T1RXXXX'), 'T1RXXXXG6'),

            'R04G3': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG3'),

            'R05G5': sum_amount(doc_values.get('T3RXXXX'), 'T3RXXXXG5'),
        })

        return doc_values

    @api.model
    def _recompute_values_J0200625(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 3

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R01G5': sum_amount(doc_values.get('T1RXXXX'), 'T1RXXXXG5'),
            'R01G7': sum_amount(doc_values.get('T1RXXXX'), 'T1RXXXXG7'),
        })

        return doc_values

    @api.model
    def _recompute_values_J0299825(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 4

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R05G4': sum_amount(doc_values.get('T1RXXXX'), 'T1RXXXXG4'),

            'R09G3': sum_amount(doc_values.get('T4RXXXX'), 'T4RXXXXG3'),

            'R010G4': sum_amount(doc_values.get('T5RXXXX'), 'T5RXXXXG4'),
        })

        return doc_values

    @api.model
    def _recompute_values_J0299325(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 5

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        _T2RXXXX = doc_values.get('T2RXXXX')

        doc_values.update({
            'R011G4': sum_amount(doc_values.get('T11RXXXX'), 'T11RXXXXG4'),
            'R012G4': sum_amount(doc_values.get('T12RXXXX'), 'T12RXXXXG4'),
            'R01G4': 0,     # see below

            'R02G4': 0,     # see below
            'R02G5': sum_amount(_T2RXXXX, 'T2RXXXXG5'),
            'R02G6': sum_amount(_T2RXXXX, 'T2RXXXXG6'),
            'R02G7': sum_amount(_T2RXXXX, 'T2RXXXXG7'),
            'R02G8': sum_amount(_T2RXXXX, 'T2RXXXXG8'),
            'R02G9': sum_amount(_T2RXXXX, 'T2RXXXXG9'),
        })

        doc_values['R01G4'] = sum_all_by_keys(doc_values, ['R011G4', 'R012G4'])

        for row in (_T2RXXXX or []):
            row['T2RXXXXG4'] = round_amount(
                (row.get('T2RXXXXG5') or 0) * 0.2
                -
                ((row.get('T2RXXXXG6') or 0) + (row.get('T2RXXXXG7') or 0) + (row.get('T2RXXXXG8') or 0) + (row.get('T2RXXXXG9') or 0)) * 0.2
            )
        doc_values['R02G4'] = sum_amount(_T2RXXXX, 'T2RXXXXG4')

        return doc_values

    @api.model
    def _recompute_values_J0215725(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 6

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """
        doc_values.update({
            'R02G6': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG6'),
            'R02G7': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG7'),
            'R02G8': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG8'),
            'R02G9': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG9'),
            'R02G10': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG10'),
            'R02G11': sum_amount(doc_values.get('T2RXXXX'), 'T2RXXXXG11'),
        })

        return doc_values

    @api.model
    def _recompute_values_J0215825(self, all_values, doc_values):
        """ Recompute auto-computed values for APPENDIX 7

        :param all_values: all current values
        :param doc_values: document current values
        :return: updated document values
        """

        # nothing

        return doc_values

    # -------------------------------------------------------------------------
    # GENERATE (EXPORT) XML
    # -------------------------------------------------------------------------

    @api.model
    def _get_part_xml_template(self, part_name):
        return f'selferp_l10n_ua_vat.account_vat_tax_report_template_export_xml_{part_name}'

    # -------------------------------------------------------------------------
    # OTHER
    # -------------------------------------------------------------------------

    def _check_included_in_values(self):
        parts = self._get_part_names()

        self.invalidate_recordset(['values'])
        for record in self:
            values = record.values or {}
            changed = False

            for i, part_name in enumerate(parts[1:]):
                field_name = f'include_{part_name}'
                field_value = 'X' if self._fields.get(field_name) and self[field_name] else ''
                key = f'{parts[0]}_HD{i}'
                if values.get(key) != field_value:
                    values[key] = field_value
                    changed = True

            if changed:
                record.with_context(
                    skip_vat_tax_report_check_included_docs=True,
                    skip_vat_tax_report_recompute_values=True,
                ).write({
                    'values': values,
                })
