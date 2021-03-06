"""Provide the view of the prizes widget."""
import datetime

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.cache import never_cache
from apps.managers.challenge_mgr import challenge_mgr
from apps.widgets.prizes.models import Prize


def supply(request, page_name):
    """Supply view_object content, which is the prizes for this team."""
    _ = page_name
    team = request.user.get_profile().team
    prizes = _get_prizes(team)
    count = len(prizes)
    return {
        "prizes": prizes,
        "range": count,
        }


def _get_prizes(team):
    """Private method to process the prizes half of the page.
       Takes the user's team and returns a dictionary to be used in the template."""

    prize_dict = {}
    today = datetime.datetime.today()
    rounds = challenge_mgr.get_all_round_info()["rounds"]

    round_name = None
    for prize in Prize.objects.all():
        if round_name != prize.round_name:
            # a new round
            round_name = prize.round_name
            prize_dict[round_name] = []

        if today < rounds[round_name]["start"]:
            # If the round happens in the future, we don't care who the leader is.
            prize.current_leader = "TBD"
        else:
            # If we are in the middle of the round, display the current leader.
            if today < rounds[round_name]["end"]:
                prize.current_leader = prize.leader(team)
            else:
                prize.winner = prize.leader(team)

        prize_dict[round_name].append(prize)

    return prize_dict


@never_cache
@user_passes_test(lambda u: u.is_staff, login_url="/landing")
def prize_form(request, prize_id):
    """Supply the prize form."""
    _ = request
    prize = get_object_or_404(Prize, pk=prize_id)
    prize.winner = prize.leader().user
    return render_to_response('view_prizes/form.txt', {
        'raffle': False,
        'prize': prize,
        'round': prize.round_name
    }, context_instance=RequestContext(request), mimetype='text/plain')
