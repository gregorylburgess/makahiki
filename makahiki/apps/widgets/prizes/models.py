"""Implements the model for prize management."""
from django.db import models
from apps.managers.player_mgr import player_mgr
from apps.managers.resource_mgr import resource_mgr

from apps.managers.team_mgr import team_mgr
from apps.managers.team_mgr.models import Group, Team
from apps.utils.utils import media_file_path
from apps.widgets.resource_goal import resource_goal


_MEDIA_LOCATION = "prizes"
"""location for uploaded files."""


class Prize(models.Model):
    """Represents a prize in the system."""
    AWARD_TO_CHOICES = (
        ("individual_overall", "Individual (Overall)"),
        ("individual_team", "Individual (Team)"),
        ("team_overall", " Team (Overall)"),
        ("team_group", " Team (Group)"),
        )
    AWARD_CRITERIA_CHOICES = (
        ("points", "Points"),
        ("energy", "Energy"),
        ("energy_goal", "Energy Goal"),
        ("water", "Water"),
        ("water_goal", "Water Goal"),
        )

    title = models.CharField(max_length=50, help_text="The title of your prize.")
    short_description = models.TextField(
        help_text="Short description of the prize. This should include information about who " \
                  "can win it."
    )
    long_description = models.TextField(
        help_text="Additional details about the prize."
    )
    value = models.IntegerField(help_text="The value of the prize.")
    image = models.ImageField(
        max_length=1024,
        upload_to=media_file_path(_MEDIA_LOCATION),
        blank=True,
        help_text="A picture of your prize."
    )
    round_name = models.CharField(
        max_length=50,
        help_text="The round in which this prize can be won."
    )
    award_to = models.CharField(
        max_length=50,
        choices=AWARD_TO_CHOICES,
        help_text="Who the prize is awarded to.  This is used to calculate who's winning."
    )
    competition_type = models.CharField(
        max_length=50,
        choices=AWARD_CRITERIA_CHOICES,
        help_text="The 'competition' this prize is awarded to.")

    def __unicode__(self):
        return self.round_name + ": " + self.title

    class Meta:
        """meta"""
        unique_together = ("round_name", "award_to", "competition_type")
        ordering = ("round_name", "award_to", "competition_type")

    def num_awarded(self, team=None):
        """Returns the number of prizes that will be awarded for this prize."""
        _ = team
        if self.award_to in ("individual_overall", "team_overall", "group"):
            # For overall prizes, it is only possible to award one.
            return 1

        elif self.award_to in ("team_group", "individual_group"):
            # For dorm prizes, this is just the number of groups.
            return Group.objects.count()

        elif self.award_to == "individual_team":
            # This is awarded to each team.
            return Team.objects.count()

        raise Exception("Unknown award_to value '%s'" % self.award_to)

    def leader(self, team=None):
        """Return the prize leader."""
        if self.competition_type == "points":
            return self._points_leader(team)
        elif self.competition_type == "energy":
            return resource_mgr.resource_leader("energy", round_name=self.round_name)
        elif self.competition_type == "energy_goal":
            return resource_goal.resource_goal_leader("energy", round_name=self.round_name)
        elif self.competition_type == "water":
            return resource_mgr.resource_leader("water", round_name=self.round_name)
        elif self.competition_type == "water_goal":
            return resource_goal.resource_goal_leader("water", round_name=self.round_name)

    def _points_leader(self, team=None):
        """Return the point leader."""
        round_name = self.round_name
        if self.award_to == "individual_overall":
            return player_mgr.points_leader(round_name=round_name)

        elif self.award_to == "team_group":
            if team:
                leaders = team.group.team_points_leaders(num_results=1, round_name=round_name)
                if leaders:
                    return leaders[0]
            return None

        elif self.award_to == "team_overall":
            return team_mgr.team_points_leader(round_name=round_name)

        elif self.award_to == "individual_team":
            if team:
                leaders = team.points_leaders(num_results=1, round_name=round_name)
                if leaders:
                    return leaders[0]
            return None

        raise Exception("'%s' is not implemented yet." % self.award_to)
