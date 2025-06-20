odoo.define('selferp_l10n_ua_salary.work_entries_gantt', function (require) {
'use strict';


const WorkEntryControllerMixin = require('selferp_l10n_ua_salary.WorkEntryControllerMixin');
const WorkEntryGanttController = require('hr_work_entry_contract_enterprise.work_entries_gantt');


return WorkEntryGanttController.include(WorkEntryControllerMixin);


});
