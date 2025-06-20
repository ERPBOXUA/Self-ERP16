odoo.define('selferp_l10n_ua_finance_report.account_report', function (require) {
'use strict';


const core = require('web.core');
const { accountReportsWidget, M2MFilters } = require('account_reports.account_report');


const _t = core._t;


accountReportsWidget.include({
    custom_events: _.extend({}, accountReportsWidget.prototype.custom_events, {
        product_filter_changed: function(event)
        {
            const self = this;

            self.report_options.product_ids = event.data.product_ids;
            self.report_options.product_categories = event.data.product_categories;

            return self.reload().then(function ()
            {
                self.$searchview_buttons.find('.account_product_filter').click();
            });
        },
    }),


    render_searchview_buttons: function()
    {
        this._super.apply(this, arguments);

        // product filter
        if (this.report_options.product)
        {
            if (!this.products_m2m_filter)
            {
                const fields = {};
                if ('product_ids' in this.report_options)
                {
                    fields['product_ids'] = {
                        label: _t("Products"),
                        modelName: 'product.product',
                        value: this.report_options.product_ids.map(Number),
                    };
                }
                if ('product_categories' in this.report_options) {
                    fields['product_categories'] = {
                        label: _t("Categories"),
                        modelName: 'product.category',
                        value: this.report_options.product_categories.map(Number),
                    };
                }

                if (!_.isEmpty(fields))
                {
                    this.products_m2m_filter = new M2MFilters(this, fields, 'product_filter_changed');
                    this.products_m2m_filter.appendTo(this.$searchview_buttons.find('.js_account_product_m2m'));
                }
            }
            else
            {
                this.$searchview_buttons.find('.js_account_product_m2m').append(this.products_m2m_filter.$el);
            }
        }
    },


});


});
