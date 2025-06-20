from odoo import api, fields, models


class AccountTaxInspection(models.Model):
    _name = 'account.tax.inspection'
    _description = "Tax Inspection"
    _order = 'code, name'

    name = fields.Char(
        string="Name",
        required=True,
    )

    code = fields.Char(
        string="Tax Code",
        required=True,
        index=True,
    )
    area_code = fields.Char(
        string="Administrative Area Code",
        compute='_compute_code',
        store=True,
        index=True,
    )
    district_code = fields.Char(
        string="Administrative District Code",
        compute='_compute_code',
        store=True,
        index=True,
    )
    district_name = fields.Char(
        string="Administrative District",
    )

    dpi_registry_code = fields.Char(
        string="Registry Code",
    )

    type = fields.Selection(
        selection=[
            ('0', "Міністерство доходів і зборів України"),
            ('1', "Обласне головне управління"),
            ('2', "ДПI"),
            ('3', "Міська ДПI (де немає районних ДПI)"),
            ('4', "Районна ДПI (для районів міста)"),
            ('5', "Районна ДПI (для сільських районів)"),
            ('6', "Об'єднана ДПI"),
            ('7', "Міжрайонна ДПI"),
            ('8', "Спеціалізована ДПI"),
            ('9', "Міжрайонна ДПI (для міських районів)"),
            ('10', "Регіональні управління ДСАТ ДПСУ"),
            ('11', "СДПI по роботі з підприємствами ГМК"),
            ('12', "Управління ПМ"),
            ('13', "Відокремлені організаційні одиниці"),
            ('14', "Митниця"),
        ],
        string="Type",
        required=True,
        default='2',
    )

    address = fields.Char(
        string="Address",
    )
    phone = fields.Char(
        string="Phone",
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    @api.depends('code')
    @api.onchange('code')
    def _compute_code(self):
        for record in self:
            area_code = None
            district_code = None

            if record.code:
                area_code = record.code[:2]
                district_code = record.code[2:]

            record.area_code = area_code
            record.district_code = district_code

    def name_get(self):
        return [(r.id, f'{r.code} {r.name}') for r in self]

