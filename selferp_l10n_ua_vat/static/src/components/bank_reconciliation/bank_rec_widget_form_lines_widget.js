/** @odoo-module **/

import { BankRecWidgetFormLinesWidget } from "@account_accountant/components/bank_reconciliation/bank_rec_widget_form_lines_widget"
import { patch } from '@web/core/utils/patch';


patch(BankRecWidgetFormLinesWidget.prototype, 'selferp_l10n_ua_vat', {
    async removeLine(lineIndex) {
        await this._super(...arguments);

        const record = this.env.model.root;
        const lastLineIndex = record.data.lines_widget.lines.slice(-1)[0].index.value;
        if (lastLineIndex){
            await record.update({todo_command: `mount_line_in_edit,${lastLineIndex}`});
        }
    }
});
