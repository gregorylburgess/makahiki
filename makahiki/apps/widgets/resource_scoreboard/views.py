"""Handle the rendering of the energy scoreboard widget."""

from apps.managers.challenge_mgr import challenge_mgr
from apps.managers.resource_mgr import resource_mgr
from apps.widgets.resource_goal import resource_goal


def supply(request, page_name):
    """Supply the view_objects content."""
    _ = request
    _ = page_name
    return {}


def resource_supply(request, resource, page_name):
    """Supply the view_objects content.
       :return: team, goals_scoreboard, resource_round_ranks"""

    user = request.user
    team = user.get_profile().team
    round_resource_ranks = {}
    round_resource_goal_ranks = {}

    current_round = challenge_mgr.get_round_name()
    rounds = challenge_mgr.get_all_round_info()["rounds"]
    for key in rounds.keys():
        if key == current_round or page_name == "status":
            round_resource_ranks[key] = resource_mgr.resource_ranks(resource, key)
            round_resource_goal_ranks[key] = resource_goal.resource_goal_ranks(resource, key)

    resource_setting = resource_mgr.get_resource_setting(resource)
    return {
        "profile": user.get_profile(),
        "team": team,
        "resource": resource_setting,
        "round_resource_goal_ranks": round_resource_goal_ranks,
        "round_resource_ranks": round_resource_ranks,
        }
