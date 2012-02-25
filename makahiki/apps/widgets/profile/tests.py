import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from managers.team_mgr.models import Team
from widgets.smartgrid.models import Activity, ActivityMember, Commitment, CommitmentMember
from widgets.quests.models import Quest

class ProfileFunctionalTestCase(TestCase):
    fixtures = ["base_teams.json"]

    def setUp(self):
        self.user = User.objects.create_user("user", "user@test.com", password="changeme")
        self.team = Team.objects.all()[0]
        profile = self.user.get_profile()
        profile.team = self.team
        profile.setup_complete = True
        profile.setup_profile = True
        profile.save()

        self.client.login(username="user", password="changeme")

    def testIndex(self):
        """Check that we can load the index page."""
        response = self.client.get(reverse("profile_index"))
        self.failUnlessEqual(response.status_code, 200)

    def testProfileUpdate(self):
        """Tests updating the user's profile."""
        # Construct a valid form
        user_form = {
            "display_name": "Test User",
            "about": "I rock",
            "contact_email": "user@test.com",
            "contact_text": "8088675309",
            "contact_carrier": "tmobile",
            }
        # Test posting a valid form.
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "Your changes have been saved",
            msg_prefix="Successful form update should have a success message.")

        # Try getting the form again to see if info sticked.
        response = self.client.get(reverse("profile_index"))
        self.assertContains(response, "user@test.com", count=1,
            msg_prefix="Contact email should be saved.")
        self.assertContains(response, "808-867-5309", count=1,
            msg_prefix="Phone number should be saved.")
        self.assertContains(response, '<option value="tmobile" selected="selected">',
            msg_prefix="Carrier should be saved.")

        # Try posting the form again.
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "Your changes have been saved",
            msg_prefix="Second form update should have a success message.")

        # Test posting without a name
        user_form.update({"display_name": ""})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "This field is required",
            msg_prefix="User should not have a valid display name.")

        # Test posting with whitespace as a name
        user_form.update({"display_name": "    "})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "This field is required",
            msg_prefix="User should not have a valid display name.")

        # Test posting a name that is too long.
        letters = "abcdefghijklmnopqrstuvwxyz"
        user_form.update({"display_name": letters})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertNotContains(response, "Your changes have been saved",
            msg_prefix="Profile with long name should not be valid.")

        # Test posting without a valid email
        user_form.update({"display_name": "Test User", "contact_email": "foo"})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "Enter a valid e-mail address",
            msg_prefix="User should not have a valid email address")

        # Test posting without a valid phone number
        user_form.update({"contact_email": "user@test.com", "contact_text": "foo"})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "Phone numbers must be in XXX-XXX-XXXX format.",
            msg_prefix="User should not have a valid contact number.")

    def testProfileWithDupName(self):
        user = User.objects.create_user("user2", "user2@test.com")
        profile = user.get_profile()
        profile.name = "Test U."
        profile.save()

        user_form = {
            "display_name": "Test U.",
            "about": "I rock",
            "stay_logged_in": True,
            "contact_email": "user@test.com",
            "contact_text": "8088675309",
            "contact_carrier": "tmobile",
            }
        # Test posting form with dup name.
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name should raise an error.")

        user_form.update({"display_name": "  Test U.     "})
        # Test posting a form with a dup name with a lot of whitespace.
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        # print response.content
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name with whitespace should raise an error.")
        self.assertContains(response, "Test U.", count=1,
            msg_prefix="This should only be in the form and in the error message.")

        user_form.update({"display_name": "Test   U."})
        response = self.client.post(reverse("profile_index"), user_form, follow=True)
        # print response.content
        self.assertContains(response, "Please use another name.",
            msg_prefix="Duplicate name with internal whitespace should raise an error.")


    def testActivityAchievement(self):
        """Check that the user's activity achievements are loaded."""
        activity = Activity(
            title="Test activity",
            description="Testing!",
            duration=10,
            point_value=10,
            pub_date=datetime.datetime.today(),
            expire_date=datetime.datetime.today() + datetime.timedelta(days=7),
            confirm_type="text",
            type="activity",
            is_canopy=True
        )
        activity.save()

        # Test that profile page has a pending activity.
        member = ActivityMember(user=self.user, activity=activity, approval_status="approved")
        member.save()

        response = self.client.get(reverse("profile_index"))
        self.assertContains(response,
            reverse("activity_task", args=(activity.type, activity.slug,)))
        self.assertContains(response, "Canopy Activity:")
        self.assertContains(response, "%d&nbsp;(Karma)" % activity.point_value)

        # Test adding an event to catch a bug.
        event = Activity(
            title="Test event",
            description="Testing!",
            duration=10,
            point_value=10,
            pub_date=datetime.datetime.today(),
            expire_date=datetime.datetime.today() + datetime.timedelta(days=7),
            confirm_type="text",
            type="event",
        )
        event.save()

        member = ActivityMember(user=self.user, activity=event, approval_status="pending")
        member.save()
        response = self.client.get(reverse("profile_index"))
        self.assertContains(response,
            reverse("activity_task", args=(activity.type, activity.slug,)))
        self.assertContains(response, "Pending")
        self.assertContains(response, "Activity:")
        self.assertContains(response, "Event:")
        self.assertNotContains(response, "You have nothing in progress or pending.")

    def testCommitmentAchievement(self):
        """Check that the user's commitment achievements are loaded."""
        commitment = Commitment(
            title="Test commitment",
            description="A commitment!",
            point_value=10,
            type="commitment",
            slug="test-commitment",
        )
        commitment.save()

        # Test that profile page has a pending activity.
        member = CommitmentMember(user=self.user, commitment=commitment)
        member.save()
        response = self.client.get(reverse("profile_index"))
        self.assertContains(response,
            reverse("activity_task", args=(commitment.type, commitment.slug,)))
        self.assertContains(response, "In Progress")
        self.assertContains(response, "Commitment:")
        self.assertNotContains(response, "You have nothing in progress or pending.")

        # Test that the profile page has a rejected activity
        member.award_date = datetime.datetime.today()
        member.save()
        response = self.client.get(reverse("profile_index"))
        self.assertContains(response,
            reverse("activity_task", args=(commitment.type, commitment.slug,)))
        self.assertNotContains(response, "You have not been awarded anything yet!")
        self.assertContains(response, "You have nothing in progress or pending.")

    def testVariablePointAchievement(self):
        """Test that a variable point activity appears correctly in the my achievements list."""
        activity = Activity(
            title="Test activity",
            slug="test-activity",
            description="Variable points!",
            duration=10,
            point_range_start=5,
            point_range_end=314160,
            pub_date=datetime.datetime.today(),
            expire_date=datetime.datetime.today() + datetime.timedelta(days=7),
            confirm_type="text",
            type="activity",
        )
        activity.save()

        points = self.user.get_profile().points
        member = ActivityMember.objects.create(
            user=self.user,
            activity=activity,
            approval_status="approved",
            points_awarded=314159,
        )
        member.save()

        self.assertEqual(self.user.get_profile().points, points + 314159,
            "Variable number of points should have been awarded.")

        # Kludge to change point value for the info bar.
        profile = self.user.get_profile()
        profile.add_points(3, datetime.datetime.today(), "test")
        profile.save()

        response = self.client.get(reverse("profile_index"))
        self.assertContains(response,
            reverse("activity_task", args=(activity.type, activity.slug,)))
        # Note, this test may break if something in the page has the value 314159.  Try finding another suitable number.
        # print response.content
        self.assertContains(response, "314159", count=1,
            msg_prefix="314159 points should appear for the activity.")

    def testSocialBonusAchievement(self):
        """Check that the social bonus appears in the my achievements list."""
        # Create a second test user.
        user2 = User.objects.create_user("user2", "user2@test.com")
        event = Activity.objects.create(
            title="Test event",
            slug="test-event",
            description="Testing!",
            duration=10,
            point_value=10,
            social_bonus=10,
            pub_date=datetime.datetime.today(),
            expire_date=datetime.datetime.today() + datetime.timedelta(days=7),
            confirm_type="code",
            type="event",
            event_date=datetime.datetime.today(),
        )

        # Create membership for the two users.
        ActivityMember.objects.create(
            user=self.user,
            activity=event,
            approval_status="approved",
            social_email="user2@test.com",
        )
        ActivityMember.objects.create(
            user=user2,
            activity=event,
            approval_status="approved",
            social_email="user@test.com",
        )

        response = self.client.get(reverse("profile_index"))
        self.assertContains(response, reverse("activity_task", args=(event.type, event.slug,)))
        entry = "Event: Test event (Social Bonus)"
        self.assertContains(response, entry, count=1,
            msg_prefix="Achievements should contain a social bonus entry")

    def testQuestAchievement(self):
        quest = Quest(
            name="Test quest",
            quest_slug="test_quest",
            description="test quest",
            level=1,
            unlock_conditions="True",
            completion_conditions="True",
        )
        quest.save()

        # Accept the quest, which should be automatically completed.
        response = self.client.post(
            reverse("quests_accept", args=(quest.quest_slug,)),
            follow=True,
            HTTP_REFERER=reverse("home_index"),
        )
        response = self.client.get(reverse("profile_index"))
        self.assertContains(response, "Quest: Test quest", count=1,
            msg_prefix="Achievements should contain a social bonus entry")
    
    