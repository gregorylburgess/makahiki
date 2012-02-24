import datetime
import re

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from managers.settings_mgr import get_current_round, get_current_round_info

from managers.team_mgr.models import Team
from widgets.raffle.models import RafflePrize

class RafflePrizesTestCase(TestCase):
    fixtures = ["base_teams.json"]

    def setUp(self):
        """Set up rounds, team, and a user."""
        # Set up rounds.
        self.saved_rounds = settings.COMPETITION_ROUNDS
        self.saved_start = settings.COMPETITION_START
        self.saved_end = settings.COMPETITION_END
        start = datetime.date.today() - datetime.timedelta(days=8)
        end1 = start + datetime.timedelta(days=7)
        end2 = start + datetime.timedelta(days=14)

        settings.COMPETITION_ROUNDS = {
            "Round 1": {
                "start": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end1.strftime("%Y-%m-%d %H:%M:%S"),
                },
            "Round 2": {
                "start": end1.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end2.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }
        settings.COMPETITION_START = start.strftime("%Y-%m-%d %H:%M:%S")
        settings.COMPETITION_END = end2.strftime("%Y-%m-%d %H:%M:%S")

        # Set up user
        self.user = User.objects.create_user("user", "user@test.com", password="changeme")
        team = Team.objects.all()[0]
        profile = self.user.get_profile()
        profile.team = team
        profile.setup_complete = True
        profile.setup_profile = True
        profile.save()

        self.client.login(username="user", password="changeme")

    def testIndex(self):
        """Check that we can load the index page."""
        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 2",
            value=5,
        )
        raffle_prize.save()

        response = self.client.get(reverse("prizes_index"))
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, "Round 2 Raffle",
            msg_prefix="We should be in round 2 of the raffle.")
        self.assertContains(response,
            "Your total raffle tickets: 0 Allocated right now: 0 Available: 0",
            msg_prefix="User should not have any raffle tickets.")
        deadline = get_current_round_info()["end"] - datetime.timedelta(hours = 2)
        date_string =  deadline.strftime("%A, %B %d, %Y, ")
        # Workaround since strftime doesn't remove the leading 0 in hours.
        hour = deadline.hour
        if hour == 0:
            hour = hour + 12
        elif hour > 12:
            hour = hour - 12
        date_string = date_string + str(hour) + deadline.strftime("%p")
        # Another workaround for days because of the leading 0
        date_string = re.sub(r"\b0", "", date_string)
        self.assertContains(response, "Deadline for Round 2 submissions: " + date_string,
            msg_prefix="Raffle should have the correct deadline.")

        # Give the user some points and see if their tickets update.
        profile = self.user.get_profile()
        profile.add_points(25, datetime.datetime.today(), "test")
        profile.save()
        response = self.client.get(reverse("prizes_index"))
        self.assertContains(response,
            "Your total raffle tickets: 1 Allocated right now: 0 Available: 1",
            msg_prefix="User should have 1 raffle ticket.")

    def testAddRemoveTicket(self):
        """Test that we can add and remove a ticket for a prize."""
        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 2",
            value=5,
        )
        raffle_prize.save()

        profile = self.user.get_profile()
        profile.add_points(25, datetime.datetime.today(), "test")
        profile.save()

        # Test that we can add a ticket.
        response = self.client.get(reverse("prizes_index"))
        self.assertContains(response, reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should be a url to add a ticket.")

        # Test adding a ticket to a prize.
        response = self.client.post(reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
            "Your total raffle tickets: 1 Allocated right now: 1 Available: 0",
            msg_prefix="User should have one allocated ticket.")
        self.assertContains(response, reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should be an url to remove a ticket.")
        self.assertNotContains(response, reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should not be an url to add a ticket.")

        # Test adding another ticket to the prize.
        profile.add_points(25, datetime.datetime.today(), "test")
        profile.save()
        response = self.client.post(reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            follow=True)
        self.assertContains(response,
            "Your total raffle tickets: 2 Allocated right now: 2 Available: 0",
            msg_prefix="User should have two allocated tickets.")

        # Test removing a ticket.
        response = self.client.post(reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            follow=True)
        self.assertContains(response,
            "Your total raffle tickets: 2 Allocated right now: 1 Available: 1",
            msg_prefix="User should have one allocated ticket and one available.")
        self.assertContains(response, reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should be a url to add a ticket.")
        self.assertContains(response, reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should be an url to remove a ticket.")

    def testAddRemoveWithoutTicket(self):
        """Test that the user cannot remove a ticket from a prize they did not allocate tickets in."""
        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 1",
            value=5,
        )
        raffle_prize.save()

        # Test removing a ticket.
        response = self.client.post(reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
            "Your total raffle tickets: 0 Allocated right now: 0 Available: 0",
            msg_prefix="User should have no tickets available")
        self.assertNotContains(response, reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should not be a url to add a ticket.")
        self.assertNotContains(response, reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should not be a url to remove a ticket.")

    def testAddWithoutTicket(self):
        """
        Test that the user cannot add a ticket to a raffle if they don't have any tickets.
        """
        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 1",
            value=5,
        )
        raffle_prize.save()

        # Test adding a ticket.
        response = self.client.post(reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
            "Your total raffle tickets: 0 Allocated right now: 0 Available: 0",
            msg_prefix="User should have no tickets available")
        self.assertNotContains(response, reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should not be a url to add a ticket.")
        self.assertNotContains(response, reverse("raffle_remove_ticket", args=(raffle_prize.id,)),
            msg_prefix="There should not be a url to remove a ticket.")

    def testAfterDeadline(self):
        """
        Test what happens when the page is accessed after the deadline.
        """
        end = datetime.datetime.today() + datetime.timedelta(hours = 1)
        settings.COMPETITION_ROUNDS["Round 2"]["end"] = end.strftime("%Y-%m-%d %H:%M:%S")
        settings.COMPETITION_END = end.strftime("%Y-%m-%d %H:%M:%S")

        response = self.client.get(reverse("prizes_index"))
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, "The raffle is now over.")

    def testPrizeOutsideOfRound(self):
        """
        Test that a raffle prize outside of the round does not appear in the list.
        """

        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 1",
            value=5,
        )
        raffle_prize.save()

        response = self.client.get(reverse("prizes_index"))
        self.failUnlessEqual(response.status_code, 200)
        self.assertNotContains(response, "Test raffle prize")

        # Try allocating a ticket to this prize.
        raffle_prize = RafflePrize(
            title="Test raffle prize",
            description="A raffle prize for testing",
            round_name="Round 2",
            value=5,
        )
        raffle_prize.save()

        end = datetime.datetime.today() + datetime.timedelta(hours = 1)
        settings.COMPETITION_ROUNDS["Round 2"]["end"] = end.strftime("%Y-%m-%d %H:%M:%S")
        settings.COMPETITION_END = end.strftime("%Y-%m-%d %H:%M:%S")

        response = self.client.post(reverse("raffle_add_ticket", args=(raffle_prize.id,)),
            follow=True)
        print response
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, "The raffle for this round is over.")

    def tearDown(self):
        """
        Restores saved settings.
        """
        # Restore rounds.
        settings.COMPETITION_ROUNDS = self.saved_rounds
        settings.COMPETITION_START = self.saved_start
        settings.COMPETITION_END = self.saved_end