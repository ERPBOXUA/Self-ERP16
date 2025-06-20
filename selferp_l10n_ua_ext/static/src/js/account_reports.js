odoo.define('selferp_l10n_ua_ext.account_report', function (require) {
'use strict';


const core = require('web.core');
const { accountReportsWidget, M2MFilters } = require('account_reports.account_report');


const _t = core._t;


accountReportsWidget.include({
    custom_events: _.extend({}, accountReportsWidget.prototype.custom_events, {
        account_filter_changed: function(event)
        {
            const self = this;

            self.report_options.account_ids = event.data.account_ids;

            return self.reload().then(function ()
            {
                self.$searchview_buttons.parent().find('.o_account_reports_filter_account_type > button.dropdown-toggle').click();
            });
        },
    }),


    render_searchview_buttons: function()
    {
        this._super.apply(this, arguments);

        // partner filter
        if (this.report_options.filter_accounts)
        {
            if (!this.accounts_m2m_filter)
            {
                const fields = {};
                if ('account_ids' in this.report_options)
                {
                    fields['account_ids'] = {
                        label: _t("Accounts"),
                        modelName: 'account.account',
                        value: this.report_options.account_ids.map(Number),
                    };
                }

                if (!_.isEmpty(fields))
                {
                    this.accounts_m2m_filter = new M2MFilters(this, fields, 'account_filter_changed');
                    this.accounts_m2m_filter.appendTo(this.$searchview_buttons.find('.js_account_account_m2m'));
                }
            }
            else
            {
                this.$searchview_buttons.find('.js_account_account_m2m').append(this.accounts_m2m_filter.$el);
            }
        }
    },


});


});
