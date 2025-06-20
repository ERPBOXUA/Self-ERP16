/** @odoo-module **/


import { registry } from '@web/core/registry';
import { formatMonetary } from '@web/views/fields/formatters';
import { TaxTotalsComponent } from '@account/components/tax_totals/tax_totals';
import { patch } from '@web/core/utils/patch';


patch(TaxTotalsComponent.prototype, 'selferp_l10n_ua_vat', {

    // @override
    _computeTotalsFormat()
    {
        this._super(...arguments);

        if (this.totals)
        {
            if ('amount_paid' in this.totals)
            {
                this.totals.formatted_amount_paid = this._format(this.totals.amount_paid);
            }
            if ('amount_outstanding_payment' in this.totals)
            {
                this.totals.formatted_amount_outstanding_payment = this._format(this.totals.amount_outstanding_payment);
            }
        }
    }


});


export class TaxTableTotalsComponent extends TaxTotalsComponent {

    formatData(props)
    {
        super.formatData(...arguments);

        if (this.totals)
        {
            const currencyFmtOpts = { currencyId: props.record.data.currency_id && props.record.data.currency_id[0] };

            if ('vat_base_total' in this.totals)
            {
                this.totals.formatted_vat_base_total = formatMonetary(this.totals.vat_base_total, currencyFmtOpts);
            }
            if ('vat_total' in this.totals)
            {
                this.totals.formatted_vat_total = formatMonetary(this.totals.vat_total, currencyFmtOpts);
            }
        }
    }

}
TaxTableTotalsComponent.template = 'selferp_l10n_ua_vat.TaxTableTotalsComponent';


registry.category('fields').add('tax_table_totals_field', TaxTableTotalsComponent);
