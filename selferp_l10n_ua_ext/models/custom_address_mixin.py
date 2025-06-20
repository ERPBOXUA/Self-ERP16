from odoo import models


class CustomAddress(models.AbstractModel):
    _name = 'address_custom.mixin'
    _description = "Creates an address string that starts with the country and is separated by commas"

    def _get_custom_address(self, use_partner=False):
        address = ""
        if not use_partner:
            address_obj = self.company_id
        else:
            address_obj = self.partner_id

        if address_obj.country_id:
            address = address_obj.country_id.name + ', '
        if address_obj.state_id:
            address += address_obj.state_id.name + ', '
        if address_obj.city:
            address += address_obj.city + ', '
        if address_obj.street:
            address += address_obj.street + ', '
        if address_obj.street2:
            address += address_obj.street2 + ', '
        if address_obj.zip:
            address += address_obj.zip + ', '
        if address:
            address = address[:-2]

        return address
