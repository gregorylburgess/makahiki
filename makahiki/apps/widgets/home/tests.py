"""
home page tests
"""

import json
import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings

from apps.managers.player_mgr.models import Profile
from apps.test_utils import TestUtils


class HomeFunctionalTestCase(TestCase):
    """Home Test Case."""

    def setUp(self):
        """setup."""
        TestUtils.register_page_widget("home", "home")

    def testIndex(self):
        """Check that we can load the index."""
        User.objects.create_user("user", "user@test.com", password="changeme")
        self.client.login(username="user", password="changeme")

        response = self.client.get(reverse("home_index"))
        self.failUnlessEqual(response.status_code, 200)


class CompetitionMiddlewareTestCase(TestCase):
    """competition middleware test."""

    def setUp(self):
        User.objects.create_user("user", "user@test.com", password="changeme")
        self.client.login(username="user", password="changeme")

        # Save settings that will be restored later.
        self.saved_start = settings.COMPETITION_START
        self.saved_end = settings.COMPETITION_END

    def testBeforeCompetition(self):
        """
        Check that the user is redirected before the competition starts.
        """
        start = datetime.datetime.today() + datetime.timedelta(days=1)
        settings.COMPETITION_START = start
        settings.COMPETITION_END = start + datetime.timedelta(days=7)

        response = self.client.get(reverse("home_index"), follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                "widgets/home/templates/restricted.html")
        self.assertContains(response, "The competition starts in")

    def testAfterCompetition(self):
        """
        Check that the user is redirected after the competition ends.
        """
        start = datetime.datetime.today() - datetime.timedelta(days=8)
        settings.COMPETITION_START = start
        settings.COMPETITION_END = start - datetime.timedelta(days=7)

        response = self.client.get(reverse("home_index"), follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                "widgets/home/templates/restricted.html")
        self.assertContains(response, "The 2011 Kukui Cup is now over")

    def tearDown(self):
        settings.COMPETITION_START = self.saved_start
        settings.COMPETITION_END = self.saved_end


class SetupWizardFunctionalTestCase(TestCase):
    """setup widzard test cases."""

    def setUp(self):
        """setup."""
        self.user = User.objects.create_user("user",
                                             "user@test.com",
                                             password="changeme")
        TestUtils.register_page_widget("home", "home")

        self.client.login(username="user", password="changeme")

    def testDisplaySetupWizard(self):
        """Check that the setup wizard is shown for new users."""
        response = self.client.get(reverse("home_index"))
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, "Introduction: Step 1 of 6")

    def testSetupTerms(self):
        """Check that we can access the terms page of the setup wizard."""
        response = self.client.get(reverse("setup_terms"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/terms.html")
        self.assertContains(response, "/account/cas/logout?next=" +
                                      reverse("about"))
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

    def testReferralStep(self):
        """
        Test that we can record referral emails from the setup page.
        """
        user2 = User.objects.create_user("user2", "user2@test.com")

        # Test we can get the referral page.
        response = self.client.get(reverse('setup_referral'), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

        # Test referring using their own email
        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': self.user.email,
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/referral.html")
        self.assertEqual(len(response.context['form'].errors), 1,
            "Using their own email as referrer should raise an error.")

        # Test referring using the email of a user who is not in the system.
        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': 'user@foo.com',
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/referral.html")
        self.assertEqual(len(response.context['form'].errors), 1,
            'Using external email as referrer should raise an error.')

        # Test bad email.
        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': 'foo',
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form'].errors), 1,
            'Using a bad email should insert an error.')
        self.assertTemplateUsed(response, "first-login/referral.html")

        # Staff user should not be able to be referred.
        user2.is_staff = True
        user2.save()

        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': user2.email,
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form'].errors), 1,
            'Using an admin as a referrer should raise an error.')
        self.assertTemplateUsed(response, "first-login/referral.html")

        user2.is_staff = False
        user2.save()

        # Test no referrer.
        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': '',
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")

        # Test successful referrer
        response = self.client.post(reverse('setup_referral'), {
            'referrer_email': user2.email,
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.referring_user,
                         user2,
                         'User 1 should be referred by user 2.')

        # Test getting the referral page now has user2's email.
        response = self.client.get(reverse('setup_referral'), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
                            user2.email,
                            msg_prefix="Going back to referral page should " \
                                       "have second user's email.")

    def testSetupProfile(self):
        """Check that we can access the profile page of the setup wizard."""
        profile = self.user.get_profile()
        profile.name = "Test User"
        profile.save()
        response = self.client.get(reverse("setup_profile"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/profile.html")
        self.assertContains(response, profile.name)
        self.assertNotContains(response, "facebook_photo")
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

    def testSetupProfileUpdate(self):
        """Check that we can update the profile of the user in the setup
        wizard."""
        profile = self.user.get_profile()
        points = profile.points
        response = self.client.post(reverse("setup_profile"), {
            "display_name": "Test User",
            }, follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/activity.html")

        user = User.objects.get(username="user")
        self.assertEqual(points + 5, user.get_profile().points,
            "Check that the user has been awarded points.")
        self.assertTrue(user.get_profile().setup_profile,
            "Check that the user has now set up their profile.")

        # Check that updating again does not award more points.
        response = self.client.post(reverse("setup_profile"), {
            "display_name": "Test User",
            }, follow=True)
        user = User.objects.get(username="user")
        self.assertEqual(points + 5, user.get_profile().points,
            "Check that the user was not awarded any more points.")
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/activity.html")

    def testSetupProfileWithoutName(self):
        """Test that there is an error when the user does not supply a
        username."""
        _ = self.user.get_profile()
        response = self.client.post(reverse("setup_profile"), {
            "display_name": "",
            })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")

    def testSetupProfileWithDupName(self):
        """Test that there is an error when the user uses a duplicate display
         name."""
        _ = self.user.get_profile()

        user2 = User.objects.create_user("user2", "user2@test.com")
        profile2 = user2.get_profile()
        profile2.name = "Test U."
        profile2.save()

        response = self.client.post(reverse("setup_profile"), {
            "display_name": "Test U.",
            }, follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name should raise an error.")

        response = self.client.post(reverse("setup_profile"), {
            "display_name": "   Test U.    ",
            }, follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name with whitespace should raise an error.")

        response = self.client.post(reverse("setup_profile"), {
            "display_name": "Test   U.",
            }, follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "first-login/profile.html")
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name with whitespace should raise an error.")

    def testSetupActivity(self):
        """Check that we can access the activity page of the setup wizard."""
        response = self.client.get(reverse("setup_activity"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/activity.html")
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

    def testSetupQuestion(self):
        """Check that we can access the question page of the setup wizard."""
        response = self.client.get(reverse("setup_question"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/question.html")
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

    def testSetupComplete(self):
        """
        Check that we can access the complete page of the setup wizard.
        """
        # Test a normal GET request (answer was incorrect).
        response = self.client.get(reverse("setup_complete"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/complete.html")
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

        user = User.objects.get(username="user")
        self.assertTrue(user.get_profile().setup_complete,
            "Check that the user has completed the profile setup.")

        # Test a normal POST request (answer was correct).
        profile = user.get_profile()
        profile.setup_complete = False
        profile.save()

        response = self.client.post(reverse("setup_complete"), {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTemplateUsed(response, "first-login/complete.html")
        try:
            json.loads(response.content)
        except ValueError:
            self.fail("Response JSON could not be decoded.")

        user = User.objects.get(username="user")
        self.assertTrue(user.get_profile().setup_complete,
            "Check that the user has completed the profile setup.")