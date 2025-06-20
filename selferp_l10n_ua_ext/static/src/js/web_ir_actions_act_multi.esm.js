/** @odoo-module **/

/**
 * This is a copy from module Web Actions Multi by OCA for Odoo 15
 * (https://apps.odoo.com/apps/modules/15.0/web_ir_actions_act_multi/).
 *
 * Should be removed (replaced with module dependency) on release module for Odoo 16.
*/

import {registry} from "@web/core/registry";

/**
 * Handle 'ir.actions.act_multi' action
 * @param {object} action see _handleAction() parameters
 * @returns {$.Promise}
 */

async function executeMultiAction({env, action}) {
    return action.actions
        .map((item) => {
            return () => {
                return env.services.action.doAction(item);
            };
        })
        .reduce((prev, cur) => {
            return prev.then(cur);
        }, Promise.resolve());
}

registry.category("action_handlers").add("ir.actions.act_multi", executeMultiAction);
