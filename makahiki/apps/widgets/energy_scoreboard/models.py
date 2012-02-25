import datetime

from django.db import models

from managers.team_mgr.models import Team

class EnergyData(models.Model):
    team = models.ForeignKey(Team)
    date = models.DateField()
    energy = models.IntegerField(default=0)

    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    updated_at = models.DateTimeField(editable=False, auto_now=True)

    @staticmethod
    def get_overall_ranks():
        """
        get the overall ranking for all teams, return an ordered query set.
        """
        team_count = Team.objects.count()
        return EnergyData.objects.order_by("-date", "energy")[:team_count]

    @staticmethod
    def get_team_overall_rank_info(team):
        """
        get the overall rank for the team. return a dict of the rank number and usage.
        """
        for idx, rank in enumerate(EnergyData.get_overall_ranks()):
            if rank.team == team:
                return {"rank": idx + 1, "usage": rank.energy}

