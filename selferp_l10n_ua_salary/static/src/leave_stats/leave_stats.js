/* @odoo-module */

import { formatDate } from '@web/core/l10n/dates';
import { LeaveStatsComponent } from '@hr_holidays/leave_stats/leave_stats'
import { patch } from '@web/core/utils/patch';


const { DateTime } = luxon;


patch(LeaveStatsComponent.prototype, 'selferp_l10n_ua_salary.hr_leave_stats', {

    async _loadCalendarDaysById(leaves) {
        let calendarDaysById = {};
        if (leaves && leaves.length > 0) {
            let holidayTypeIds = this.state.leaves.map((leave) => leave.holiday_status_id[0]);
            let holidayTypes = await this.orm.searchRead(
                'hr.leave.type',
                [['id', 'in', holidayTypeIds]],
                ['id', 'in_calendar_days'],
            );
            if (holidayTypes && holidayTypes.length > 0) {
                holidayTypes.forEach((elem) => {
                    calendarDaysById[elem.id] = elem.in_calendar_days;
                });
            }
        }
        return calendarDaysById;
    },

    async loadLeaves(date, employee) {
        await this._super(...arguments);
        if (this.state.leaves && this.state.leaves.length > 0) {
            let calendarDaysById = await this._loadCalendarDaysById(this.state.leaves);
            this.state.leaves.forEach((leave) => {
                let typeId = leave.holiday_status_id[0];
                leave.in_calendar_days = calendarDaysById[typeId];
            });
        }
    },

    async loadDepartmentLeaves(date, department, employee) {
        if (!(department && employee && date)) {
            this.state.departmentLeaves = [];
            return;
        }

        const dateFrom = date.startOf('month');
        const dateTo = date.endOf('month');

        const departmentLeaves = await this.orm.searchRead(
            'hr.leave',
            [
                ['department_id', '=', department[0]],
                ['state', '=', 'validate'],
                ['holiday_type', '=', 'employee'],
                ['date_from', '<=', dateTo],
                ['date_to', '>=', dateFrom],
            ],
            ['employee_id', 'holiday_status_id', 'date_from', 'date_to', 'number_of_days'],
        );

        if (departmentLeaves && departmentLeaves.length) {
            let calendarDaysById = await this._loadCalendarDaysById(departmentLeaves);
            departmentLeaves.forEach((leave) => {
                let typeId = leave.holiday_status_id[0];
                leave.in_calendar_days = calendarDaysById[typeId];
            });
        }

        this.state.departmentLeaves = departmentLeaves.map((leave) => {
            return Object.assign({}, leave, {
                dateFrom: formatDate(DateTime.fromSQL(leave.date_from, { zone: 'utc' }).toLocal()),
                dateTo: formatDate(DateTime.fromSQL(leave.date_to, { zone: 'utc' }).toLocal()),
                sameEmployee: leave.employee_id[0] === employee[0],
                in_calendar_days: leave.in_calendar_days,
            });
        });
    },

});
