odoo.define('selferp_l10n_ua_salary.WorkEntryControllerMixin', function(require) {
'use strict';


const time = require('web.time');
const core = require('web.core');
const QWeb = core.qweb;


return  {
    updateButtons: function() {
        this._super.apply(this, arguments);

        if (!this.$buttons) {
            return;
        }

        this.$buttons.find('.btn-print-timesheet').on('click', this._onPrintTimesheet.bind(this));
    },

    _renderWorkEntryButtons: function () {
        let $buttons = this._super.apply(this, arguments);
        return $buttons.append(this._renderPrintTimesheetButton());
    },

    _renderPrintTimesheetButton: function() {
        return $(QWeb.render('selferp_l10n_ua_salary.work_entry_button', {}));
    },

    _onPrintTimesheet: function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        this.trigger_up('do_action', {
            action: 'selferp_l10n_ua_salary.hr_work_entry_print_action',
            options: {
                additional_context: {
                    default_date_from: time.date_to_str(this.firstDay),
                    default_date_to: time.date_to_str(this.lastDay),
                    active_employee_ids: this._getActiveEmployeeIds(),
                },
            },
        });
    },
};

});
