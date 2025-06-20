import os
import re

from collections import defaultdict
from lxml import etree

from odoo import _
from odoo.modules.module import get_resource_path
from odoo.exceptions import UserError


XMLSCHEMA_NAMESPACE_PREFIX = 'xs'
XMLSCHEMA_NAMESPACE_URL = 'http://www.w3.org/2001/XMLSchema'


def xml_prettify(xml_data):
    """ Convert given XML data (binary) to pretty string

    :param xml_data:
    :return:
    """
    parser = etree.XMLParser(remove_blank_text=True)
    xml_root = etree.fromstring(xml_data.encode('utf-8'), parser=parser)
    xml_data = etree.tostring(xml_root, encoding='UTF-8', method='xml', pretty_print=True)

    return xml_data


def xml_schema_load(doc_key):
    """ Load XML schema from file for given document ID

    :param doc_key: document ID (key)
    :return: schema xml root
    """
    schema_path = get_resource_path('selferp_l10n_ua_ext', 'schemas', f'{doc_key}.xsd')
    if not schema_path or not os.path.exists(schema_path):
        raise UserError(_("Schema not found for document %s", doc_key))

    with open(schema_path, 'r', encoding='windows-1251') as schema_file:
        return etree.parse(schema_file)


def xml_schema_lookup_type(schema_root, element_name):
    """ Try to find element type in schema

    :param schema_root: schema XML root
    :param element_name: XML element name
    :return: XML element type name or None (if not found)
    """
    if schema_root and element_name:
        element = schema_root.find(
            f'//{XMLSCHEMA_NAMESPACE_PREFIX}:element[@name="{element_name}"]',
            namespaces={XMLSCHEMA_NAMESPACE_PREFIX: XMLSCHEMA_NAMESPACE_URL},
        )
        if element is not None:
            return element.get('type')
    return None


def export_xml_extract_doc_number(doc_num):
    """ Extract document number for export XML
        from document record sequence value

    :param doc_num: document sequence value string
    :return: extracted number of document
    """
    if isinstance(doc_num, int):
        return doc_num

    return int((re.findall(r'(\d+)$', str(doc_num)) or [1])[-1])


def export_xml_create_base_head(doc_key, company, doc_num, doc_date=None, period_type='1', period_month=None, period_year=None, date_fill=None):
    """ Create base DECLARHEAD values

    :param doc_key: unique document key (name), e.g. J1201014
    :param company: company record
    :param doc_num: document number (sequence value)
    :param doc_date: document date (should be empty if period_month and period_year defined)
    :param period_type: period type (1 - month, 2 - quarter, 3 - half year, 4 - 9 month, 5 - year)
    :param period_month: period month
    :param period_year: period year
    :param date_fill: fill date (equals to document date if not defined)
    :return:
    """
    doc_num = export_xml_extract_doc_number(doc_num)
    doc_fill = date_fill or doc_date

    if not company.company_registry:
        raise UserError(_("Company ID not defined"))

    return {
        'TIN': company.company_registry,
        'C_DOC': ('J' if company.company_legal_form == 'legal' else 'F') + doc_key[1:3],
        'C_DOC_SUB': doc_key[3:6],
        'C_DOC_VER': doc_key[6:],
        'C_DOC_TYPE': '0',
        'C_DOC_CNT': str(doc_num),
        'C_REG': company.tax_inspection_id and company.tax_inspection_id.area_code or None,
        'C_RAJ': company.tax_inspection_id and company.tax_inspection_id.district_code or None,
        'PERIOD_MONTH': period_month or (doc_date and doc_date.strftime('%m')) or None,
        'PERIOD_TYPE': period_type,
        'PERIOD_YEAR': period_year or (doc_date and doc_date.strftime('%Y')) or None,
        'C_STI_ORIG': company.tax_inspection_id and company.tax_inspection_id.code or None,
        'C_DOC_STAN': 1,
        'LINKED_DOCS': None,
        'D_FILL': doc_fill and doc_fill.strftime('%d%m%Y') or None,
        'SOFTWARE': 'Odoo',
    }


def export_xml_file_name(data):
    """ Create XML file name for given params

    :param data: data set for XML
    :return: file name
    """
    return '%s%s%s%s%s%s%s%s%s%s%s%s.xml' % (
        data['C_STI_ORIG'].zfill(4),
        data['TIN'].zfill(10),
        data['C_DOC'].zfill(3),
        data['C_DOC_SUB'].zfill(3),
        data['C_DOC_VER'].zfill(2),
        data['C_DOC_STAN'],
        data['C_DOC_TYPE'].zfill(2),
        data['C_DOC_CNT'].zfill(7),
        data['PERIOD_TYPE'],
        str(data['PERIOD_MONTH']).zfill(2),
        str(data['PERIOD_YEAR']).zfill(4),
        data['C_STI_ORIG'].zfill(4),
    )


def export_xml_format_number(value, min_decimal=0, max_decimal=12):
    long = ('{:.%sf}' % max_decimal).format(value).rstrip('0').rstrip('.')
    if min_decimal:
        short = ('{:.%sf}' % min_decimal).format(value)
        if len(short) > len(long):
            return short
    return long


def export_xml_match_values_with_schema(doc_key, values):
    """ Match given values according to the schema of document.
        Means try to convert values to string regarding element types.

    :param doc_key: document ID (key)
    :param values: values dictionary
    :return: modified values dictionary
    """

    # load the schema of document
    schema_root = xml_schema_load(doc_key)

    # convert values
    return export_xml_match_values_with_schema_xml(schema_root, values)


def export_xml_match_values_with_schema_xml(schema_root, values):
    """ Match given values according to the schema XML of document.
        Means try to convert values to string regarding element types.

    :param schema_root: XML root of the schema
    :param values: values dictionary
    :return: modified values dictionary
    """
    new_values = defaultdict(lambda: None)

    # for each value
    for name, value in values.items():
        if value is not None:
            # check tables
            if isinstance(value, list):
                new_table = []
                for row in value:
                    new_row = export_xml_match_values_with_schema_xml(schema_root, row)
                    if new_row:
                        new_table.append(new_row)
                value = new_table

            else:
                # try to get type name
                type_name = xml_schema_lookup_type(schema_root, name)
                if type_name:
                    # convert value to string depending on type
                    if type_name in ('DGdecimal0', 'Decimal0Column', 'DGdecimal1', 'Decimal1Column', 'DGdecimal2', 'Decimal2Column'):
                        if isinstance(value, str):
                            value = value.strip()
                            if value:
                                value = float(value)
                            else:
                                # @TODO: check required value
                                value = None

                        if value is not None:
                            if '0' in type_name:
                                # <xs:pattern value="\-{0,1}[0-9]+(\.0{1,2}){0,1}"/>
                                if isinstance(value, str):
                                    value = value and float(value) or 0
                                value = int(value)

                            elif '1' in type_name:
                                # <xs:pattern value="\-{0,1}[0-9]+\.[0-9]{1,2}"/>
                                if isinstance(value, str):
                                    value = value and float(value) or 0
                                value = export_xml_format_number(value, min_decimal=1, max_decimal=2)

                            elif '2' in type_name:
                                # <xs:pattern value="\-{0,1}[0-9]+\.[0-9]{2}"/>
                                if isinstance(value, str):
                                    value = value and float(value) or 0
                                value = '{:.2f}'.format(value)

                    elif type_name in ('DGDate', 'DateColumn'):
                        if value:
                            value = str(value).strip().replace('.', '').zfill(8)
                        else:
                            # @TODO: check required value
                            value = None

                    elif type_name in ('DGchk', 'ChkColumn'):
                        if value and str(value).strip().lower() not in ('0', 'false'):
                            value = '1'
                        else:
                            value = '0'

                    elif type_name == 'DGHZIP':
                        # <xs:pattern value="([0-9]{5,5})"/>
                        value = str(value).strip()[:5].zfill(5)

                    elif type_name == 'DGHTEL':
                        # <xs:pattern value="[0-9 ()\-+\.,;]{4,}"/>
                        value = str(value).strip()
                        if len(value) < 4:
                            value = value.zfill(4)

            # put value
            new_values[name] = value

    # return modified values
    return new_values
