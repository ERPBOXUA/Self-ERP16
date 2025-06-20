from odoo.addons.analytic.tests.test_analytic_account import TestAnalyticAccount


#
#
# A new account.analytic.plan is creating during company creation, so we need to replace standard tests
# There is a replacing of standard tests from analytic.tests.test_analytic_account
#
#


def test_get_plans_with_option(self):
    """ Test the plans returned with applicability rules and options """
    kwargs = {'business_domain': 'general'}
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(2, len(plans_json), "Only the Default plan should be available")

    applicability = self.env['account.analytic.applicability'].create({
        'business_domain': 'general',
        'analytic_plan_id': self.analytic_plan_1.id,
        'applicability': 'mandatory',
    })
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(3, len(plans_json), "All root plans should be available")

    self.analytic_plan_1.write({'default_applicability': 'mandatory'})
    applicability.write({'applicability': 'unavailable'})
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(2, len(plans_json), "Plan 1 should be unavailable")

    kwargs = {'business_domain': 'purchase_order'}
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(3, len(plans_json), "Both plans should be available")

    kwargs = {'applicability': 'optional'}
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(3, len(plans_json), "All root plans should be available")


def test_get_plans_without_options(self):
    """ Test that the plans with the good appliability are returned without if no options are given """
    kwargs = {}
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(2, len(plans_json), "Only the Default plan should be available")

    self.analytic_plan_1.write({'default_applicability': 'mandatory'})
    plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
    self.assertEqual(3, len(plans_json), "All root plans should be available")


def test_analytic_plan_account_child(self):
    """
    Check that when an analytic account is set to the third (or more) child,
    the root plan is correctly retrieved.
    """
    self.analytic_plan = self.env['account.analytic.plan'].create({
        'name': 'Parent Plan',
        'company_id': False,
    })
    self.analytic_sub_plan = self.env['account.analytic.plan'].create({
        'name': 'Sub Plan',
        'parent_id': self.analytic_plan.id,
        'company_id': False,
    })
    self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
        'name': 'Sub Sub Plan',
        'parent_id': self.analytic_sub_plan.id,
        'company_id': False,
    })
    self.analytic_account_1 = self.env['account.analytic.account'].create({'name': 'Child Account', 'plan_id': self.analytic_sub_sub_plan.id})
    plans_json = self.env['account.analytic.plan'].get_relevant_plans()
    self.assertEqual(
        3,
        len(plans_json),
        "The parent plan should be available even if the analytic account is set on child of third generation",
    )


setattr(TestAnalyticAccount, 'test_analytic_plan_account_child', test_analytic_plan_account_child)
setattr(TestAnalyticAccount, 'test_get_plans_without_options', test_get_plans_without_options)
setattr(TestAnalyticAccount, 'test_get_plans_with_option', test_get_plans_with_option)
