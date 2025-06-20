/** @odoo-module alias=selferp_l10n_ua_vat.many2one_with_payments **/


import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { Many2XAutocomplete } from '@web/views/fields/relational_utils';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';


export class Many2XAutocompleteWithPayments extends Many2XAutocomplete {

    setup()
    {
        super.setup();
    }


    get sources()
    {
        return [{
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionTemplate: 'many2one_with_payments.Many2oneDropdownOption',
        }];
    }


    async loadOptionsSource(request)
    {
        if (this.lastProm)
        {
            this.lastProm.abort(false);
        }

        this.lastProm = this.orm.call(this.props.resModel, 'search_read', [], {
            domain: [['name', 'ilike', request]].concat(this.props.getDomain()),
            fields: ['id', 'display_name', 'amount_outstanding_payment', 'amount_outstanding_payment_formatted'],
            limit: this.props.searchLimit + 1,
            context: this.props.context,
        });
        const records = await this.lastProm;

        const options = records.map((row) => ({
            label: row.display_name,
            value: row.id,
            amount: row.amount_outstanding_payment,
            amount_formatted: row.amount_outstanding_payment_formatted,
        }));

        if (!this.props.noSearchMore && this.props.searchLimit < records.length)
        {
            options.push({
                label: _t("Search More..."),
                action: this.onSearchMore.bind(this, request),
                classList: 'o_m2o_dropdown_option o_m2o_dropdown_option_search_more',
            });
        }

        if (!records.length && !this.activeActions.create)
        {
            options.push({
                label: _t("No records"),
                classList: 'o_m2o_no_result',
                unselectable: true,
            });
        }

        return options;
    }

}


export class Many2oneWithPayments extends Many2OneField {}

Many2oneWithPayments.components = {
    ...Many2OneField.components,
    Many2XAutocomplete: Many2XAutocompleteWithPayments,
}


registry.category('fields').add('many2one_with_payments', Many2oneWithPayments);
