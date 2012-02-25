import os
import datetime

from django.db.models import Q
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.core import management

from managers.team_mgr.models import Team
from managers.player_mgr.models import Profile
from widgets.prizes.models import RaffleDeadline, RafflePrize, Prize

class Command(management.base.BaseCommand):
    help = 'Picks winners for raffle deadlines that have passed.'

    def handle(self, *args, **options):
        """
        Generates forms for winners.
        """
        deadlines = RaffleDeadline.objects.filter(end_date__lte=datetime.datetime.today())
        # Seems to be an easy way to generate round information.
        rounds = (deadline.round_name for deadline in deadlines)
        for round_name in rounds:
            self.__generate_forms(round_name)

    def __generate_forms(self, round_name):
        round_dir = 'prizes/%s' % round_name
        if not os.path.exists('prizes'):
            os.mkdir('prizes')
        if not os.path.exists(round_dir):
            os.mkdir(round_dir)

        self.__generate_raffle_forms(round_dir, round_name)
        self.__generate_prize_forms(round_dir, round_name)

    def __generate_raffle_forms(self, round_dir, round_name):
        # Get raffle prizes.
        prizes = RafflePrize.objects.filter(deadline__round_name=round_name, winner__isnull=False)
        for prize in prizes:
            # Render form
            contents = render_to_string('view_prizes/form.txt', {
                'raffle': True,
                'prize': prize,
                'round': round_name
            })

            # Write to file
            filename = 'raffle-%s-%s.txt' % (slugify(prize.title), prize.winner.username)
            f = open('%s/%s' % (round_dir, filename), 'w')
            f.write(contents)

    def __generate_prize_forms(self, round_dir, round_name):
        prizes = Prize.objects.filter(
            Q(award_to='individual_team') | Q(award_to='individual_overall'),
            round_name=round_name,
        )

        round_name = round_name if round_name != 'Overall' else None
        # Need to calculate winners for each prize.
        for prize in prizes:
            if prize.award_to == 'individual_team':
                # Need to calculate team winners for each team.
                for team in Team.objects.all():
                    leader = team.points_leaders(1, round_name)[0].user
                    prize.winner = leader
                    contents = render_to_string('view_prizes/form.txt', {
                        'raffle': False,
                        'prize': prize,
                        'round': round_name,
                        })

                    filename = '%s-%s.txt' % (team.name, leader.username)
                    f = open('%s/%s' % (round_dir, filename), 'w')
                    f.write(contents)

            else:
                leader = Profile.points_leaders(1, round_name)[0].user
                prize.winner = leader
                contents = render_to_string('view_prizes/form.txt', {
                    'raffle': False,
                    'prize': prize,
                    'round': round_name,
                    })

                filename = 'overall-%s.txt' % leader.username
                f = open('%s/%s' % (round_dir, filename), 'w')
                f.write(contents)
        