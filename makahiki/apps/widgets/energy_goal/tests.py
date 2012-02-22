from managers.team_mgr.models import Group
from managers.player_mgr.models import Profile

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from managers.team_mgr.models import Team
from widgets.energy_goal.models import TeamEnergyGoal

class EnergyFunctionalTestCase(TestCase):
    fixtures = ["base_teams.json"]

    def setUp(self):
        """Initialize a user and log them in."""
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
        response = self.client.get(reverse("energy_index"))
        self.failUnlessEqual(response.status_code, 200)

    def testEnergyScoreboard(self):
        response = self.client.get(reverse("energy_index"))
        goals = response.context["view_objects"]["energy_scoreboard"]["goals_scoreboard"]
        for goal in goals:
            self.assertEqual(goal["completions"], 0, "No team should have completed a goal.")

        goal = TeamEnergyGoal.objects.create(
            team=self.team,
            goal_usage="1.0",
            actual_usage="2.0",
        )

        response = self.client.get(reverse("energy_index"))
        goals = response.context["view_objects"]["energy_scoreboard"]["goals_scoreboard"]
        for goal in goals:
            self.assertEqual(goal["completions"], 0, "No team should have completed a goal.")

        goal = TeamEnergyGoal.objects.create(
            team=self.team,
            goal_usage="1.0",
            actual_usage="0.5",
        )

        response = self.client.get(reverse("energy_index"))
        goals = response.context["view_objects"]["energy_scoreboard"]["goals_scoreboard"]
        for team in goals:
            if team["team__name"] == self.team.name:
                # print team.teamenergygoal_set.all()
                self.assertEqual(team["completions"], 1,
                    "User's team should have completed 1 goal, but completed %d" % team[
                                                                                    "completions"])
            else:
                self.assertEqual(team["completions"], 0, "No team should have completed a goal.")


class TeamEnergyGoalTest(TestCase):
    def setUp(self):
        group = Group.objects.create(name="Test Group")
        group.save()
        self.team = Team.objects.create(
            group=group,
            name="A"
        )

        self.user = User.objects.create_user("user", "user@test.com")
        profile = self.user.get_profile()
        profile.team = self.team
        profile.save()

    def testTeamEnergyGoal(self):
        profile = self.user.get_profile()
        points = profile.points

        goal = TeamEnergyGoal(
            team=self.team,
            goal_usage=str(1.0),
            actual_usage=str(0.5),
        )
        goal.save()
        profile = Profile.objects.get(user__username="user")
        self.assertEqual(profile.points, points,
            "User that did not complete the setup process should not be awarded points.")

        profile.setup_complete = True
        profile.save()

        goal.actual_usage = "1.5"
        goal.save()
        profile = Profile.objects.get(user__username="user")
        self.assertEqual(profile.points, points,
            "Team that failed the goal should not be awarded any points.")

        goal.actual_usage = "0.5"
        goal.save()
        profile = Profile.objects.get(user__username="user")
        self.assertEqual(profile.points, points + TeamEnergyGoal.GOAL_POINTS,
            "User that setup their profile should be awarded points.")
    
    
    
