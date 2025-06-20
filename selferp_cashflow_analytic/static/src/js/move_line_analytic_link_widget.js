/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';


const { Component } = owl;


class MoveLineAnalyticLink extends Component {

    setup() {
        this.action = useService('action');
    }

    async linkRecord(event) {
        event.preventDefault();
        event.stopPropagation();
        if (this.props && this.props.record && this.props.name) {
            let fieldName = this.props.name;
            let targetModel = this.props.record.resModel;
            let targetId = this.props.record.resId;
            if (fieldName && targetModel && targetId && this.props.record && this.props.record.data['can_change_cash_flow_analytic_account']) {
                const action = {
                    type: 'ir.actions.act_window',
                    name: this.env._t("Select"),
                    res_model: 'account.move.line.analytic.link',
                    views: [[false, 'form']],
                    view_mode: 'form',
                    target: 'new',
                    context: {
                        default_move_line_id: targetId,
                        default_cash_flow_analytic_account_id: this.props.value ? this.props.value[0] : false,
                    },
                };
                const options = {
                    onClose: () => {
                        this.props.record.model.load({resId: targetId});
                    },
                };
                await this.action.doAction(action, options);
            }
        }
    }

}

MoveLineAnalyticLink.template = 'selferp_cashflow_analytic.MoveLineAnalyticLink';
registry.category('fields').add('move2analytic_link', MoveLineAnalyticLink);
