from odoo import models, api, Command


def _install_analytics(self, group_analytic=None, immediate_dependencies=True):
    if self:
        group_analytic = group_analytic or self.env.ref('analytic.group_analytic_accounting', raise_if_not_found=False)

        if group_analytic:
            for user in self:
                if group_analytic not in user.groups_id:
                    super(ResUsers, user).write({'groups_id': [Command.link(group_analytic.id)]})
                if user.has_group('base.group_system'):
                    config = self.env['res.config.settings'].with_user(user.id).create({
                        'group_analytic_accounting': True
                    })
                    config.execute()

            budget_module = self.env['ir.module.module'].sudo().search([('name', '=', 'account_budget')])
            if budget_module and budget_module.state != 'installed':
                if immediate_dependencies:
                    budget_module.button_immediate_install()
                else:
                    budget_module.button_install()


def _uninstall_analytics(self, group_analytic=None):
    if self:
        group_analytic = group_analytic or self.env.ref('analytic.group_analytic_accounting', raise_if_not_found=False)

        if group_analytic:
            for user in self:
                if group_analytic in user.groups_id:
                    super(ResUsers, user).write({'groups_id': [Command.unlink(group_analytic.id)]})
                if user.has_group('base.group_system'):
                    config = self.env['res.config.settings'].with_user(user.id).create({
                        'group_analytic_accounting': False
                    })
                    config.execute()


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        group_account_user = self.env.ref('account.group_account_user', raise_if_not_found=False)
        group_analytic = self.env.ref('analytic.group_analytic_accounting', raise_if_not_found=False)
        if group_account_user and group_analytic:
            to_add_analytic = records.filtered(lambda rec: group_account_user in rec.groups_id)
            if to_add_analytic:
                _install_analytics(to_add_analytic, group_analytic=group_analytic)

        return records

    def write(self, values):
        write_groups = 'groups_id' in (self._remove_reified_groups(values) or {})
        accountants_before = set()
        group_account_user = self.env.ref('account.group_account_user', raise_if_not_found=False)
        group_analytic = self.env.ref('analytic.group_analytic_accounting', raise_if_not_found=False)
        if write_groups and group_account_user and group_analytic:
            accountants_before = {rec.id for rec in self if group_account_user in rec.groups_id}
        else:
            write_groups = False

        result = super().write(values)

        if write_groups:
            accountants_after = {rec.id for rec in self if group_account_user in rec.groups_id}
            to_add_analytic = [
                rec.id
                for rec in self
                if rec.id not in accountants_before and rec.id in accountants_after
            ]
            to_remove_analytic = [
                rec.id
                for rec in self
                if rec.id in accountants_before and rec.id not in accountants_after
            ]
            if to_add_analytic:
                to_add_analytic = self.env['res.users'].sudo().browse(to_add_analytic)
                _install_analytics(to_add_analytic, group_analytic=group_analytic)
            if to_remove_analytic:
                to_remove_analytic = self.env['res.users'].sudo().browse(to_remove_analytic)
                _uninstall_analytics(to_remove_analytic, group_analytic=group_analytic)

        return result
