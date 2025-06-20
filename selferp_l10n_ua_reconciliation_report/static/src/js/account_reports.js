/** @odoo-module */

import { registry } from '@web/core/registry';
import { download } from '@web/core/network/download';


async function executeReconciliationReportDownload({ env, action }) {
    env.services.ui.block();
    const url = '/account_reports';
    const data = action.data;
    try {
        await download({ url, data });
    } finally {
        env.services.ui.unblock();
    }
}

registry
    .category('action_handlers')
    .add('ir_actions_reconciliation_report_download', executeReconciliationReportDownload);
