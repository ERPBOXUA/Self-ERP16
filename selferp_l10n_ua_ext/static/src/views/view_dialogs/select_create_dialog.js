/** @odoo-module **/

import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { patch } from "@web/core/utils/patch";

// This patch allows to control of the appearance of the search panel on the select/create dialog when working with hierarchical models.
// To show the search panel in the select/create dialog (which is hidden by default) an appropriate m2o field must have context with
// `'use_search_panel'=True` value is set
// Warning: Do not use this feature with models which does not support hierarchy view or empty search panel will appear on the dialog!!!
patch(SelectCreateDialog.prototype, 'selferp_l10n_ua_ext.search_panel', {
    setup() {
        this._super(...arguments);
        if (this.props.type === 'list' && this.props.context && this.props.context.use_search_panel) {
            let display = this.baseViewProps.display || {};
            display.searchPanel = true;
            this.baseViewProps.display = display;
        }
    }
});
