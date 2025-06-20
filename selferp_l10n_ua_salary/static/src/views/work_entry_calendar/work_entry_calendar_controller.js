/** @odoo-module **/


import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
import { WorkEntryCalendarController } from '@hr_work_entry_contract/views/work_entry_calendar/work_entry_calendar_controller';


patch(WorkEntryCalendarController.prototype, 'selferp_l10n_ua_salary.work_entries_calendar', {

    setup() {
        this._super(...arguments);
        this.action = useService('action');
    },

    onPrintTimesheet(event) {
        event.preventDefault();
        event.stopImmediatePropagation();

        const range = this.model.computeRange();

        const additionalContext = {
            default_date_from: range && range.start && range.start.toSQLDate() || false,
            default_date_to: range && range.end && range.end.toSQLDate() || false,
            active_employee_ids: this.getEmployeeIds(),
        }

        this.action.doAction(
            'selferp_l10n_ua_salary.hr_work_entry_print_action',
            {
                additionalContext: additionalContext,
            }
        );
    },

});
