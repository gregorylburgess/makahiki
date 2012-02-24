import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings

from managers.team_mgr.models import Team
from widgets.prizes.models import Prize

class PrizesFunctionalTestCase(TestCase):
    fixtures = ["base_teams.json", "test_prizes.json"]

    def setUp(self):
        """Set up a team and log in."""
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
        response = self.client.get(reverse("prizes_index"))
        self.failUnlessEqual(response.status_code, 200)

        for prize in Prize.objects.all():
            self.assertContains(response, prize.title, msg_prefix="Prize not found on prize page")

    def testLeadersInRound1(self):
        """Test that the leaders are displayed correctly in round 1."""
        saved_rounds = settings.COMPETITION_ROUNDS
        saved_start = settings.COMPETITION_START
        saved_end = settings.COMPETITION_END
        start = datetime.date.today()
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

        profile = self.user.get_profile()
        profile.name = "Test User"
        profile.add_points(10, datetime.datetime.today(), "test")
        team = profile.team
        profile.save()

        response = self.client.get(reverse("prizes_index"))
        self.assertContains(response, "Current leader: " + str(profile), count=2,
            msg_prefix="Individual prizes should have user as the leader.")
        self.assertContains(response, "Current leader: " + str(team), count=2,
            msg_prefix="Team points prizes should have team as the leader")
        self.assertContains(response, "Current leader: <span id='round-1-leader'></span>", count=1,
            msg_prefix="Span for round 1 energy prize should be inserted.")
        self.assertNotContains(response, "Current leader: <span id='round-2-leader'></span>",
            msg_prefix="Span for round 2 energy prize should not be inserted.")
        self.assertContains(response, "Current leader: <span id='overall-leader'></span>", count=1,
            msg_prefix="Span for round 1 energy prize should be inserted.")
        self.assertContains(response, "Current leader: TBD", count=3,
            msg_prefix="Round 2 prizes should not have a leader yet.")

        # Test XSS vulnerability.
        profile.name = '<div id="xss-script"></div>'
        profile.save()

        response = self.client.get(reverse("prizes_index"))
        self.assertNotContains(response, profile.name,
            msg_prefix="<div> tag should be escaped.")

        # Restore rounds.
        settings.COMPETITION_ROUNDS = saved_rounds
        settings.COMPETITION_START = saved_start
        settings.COMPETITION_END = saved_end

    def testLeadersInRound2(self):
        """Test that the leaders are displayed correctly in round 2."""
        saved_rounds = settings.COMPETITION_ROUNDS
        saved_start = settings.COMPETITION_START
        saved_end = settings.COMPETITION_END
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

        profile = self.user.get_profile()
        profile.add_points(10, datetime.datetime.today(), "test")
        profile.name = "Test User"
        team = profile.team
        profile.save()

        response = self.client.get(reverse("prizes_index"))
        self.assertContains(response, "Winner: ", count=3,
            msg_prefix="There should be winners for three prizes.")
        self.assertContains(response, "Current leader: " + str(profile), count=2,
            msg_prefix="Individual prizes should have user as the leader.")
        self.assertContains(response, "Current leader: <span id='round-2-leader'></span>", count=1,
            msg_prefix="Span for round 2 energy prize should be inserted.")
        self.assertContains(response, "Current leader: " + str(team), count=2,
            msg_prefix="Team points prizes should have team as the leader")

        # Test XSS vulnerability.
        profile.name = '<div id="xss-script"></div>'
        profile.save()

        response = self.client.get(reverse("prizes_index"))
        self.assertNotContains(response, profile.name,
            msg_prefix="<div> tag should be escaped.")

        # Restore rounds.
        settings.COMPETITION_ROUNDS = saved_rounds
        settings.COMPETITION_START = saved_start
        settings.COMPETITION_END = saved_end
