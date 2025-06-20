/** @odoo-module **/

import { BankRecWidgetFormInnerTabAmlsRenderer } from '@account_accountant/components/bank_reconciliation/bank_rec_widget_form_inner_tab_amls'
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';


patch(BankRecWidgetFormInnerTabAmlsRenderer.prototype, 'selferp_l10n_ua_vat', {

    setup() {
        this._super(...arguments);
        this.bankRecService = useService("bank_rec_widget");
    },

    async onCellClicked(record, column, ev) {
        await this._super(...arguments);

        if (this.stLineState.formRestoreData) {
            let formRestoreData = this.stLineState.formRestoreData;
            if (_.isString(formRestoreData)) {
                formRestoreData = JSON.parse(formRestoreData);
            }

            if (formRestoreData.lines_widget) {
                const lastLineIndex = formRestoreData.lines_widget.lines.slice(-1)[0].index.value;
                if (lastLineIndex) {
                    this.bankRecService.todoCommandListeners['form-todo-command'](`mount_line_in_edit,${lastLineIndex}`)
                }
            }
        }
    },

});
