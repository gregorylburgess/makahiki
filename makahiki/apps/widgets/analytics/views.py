# Create your views here.
import datetime

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Count, F, Min

from widgets.smartgrid import get_popular_activities, get_popular_commitments, get_popular_events
from widgets.smartgrid.models import ActivityBase, Activity, ActivityMember
from widgets.energy_goal.models import TeamEnergyGoal
from managers.team_mgr.models import Team
from managers.player_mgr.models import Profile
from managers.score_mgr.models import ScoreboardEntry
from widgets.prizes.models import RaffleDeadline
from widgets.quests.models import Quest

@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def home(request):
    return render_to_response("status/home.html", {}, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def points_scoreboard(request):
    profiles = Profile.objects.filter(
        points__gt=0,
    ).order_by("-points", "-last_awarded_submission").values("name", "points", 'user__username')

    canopy_members = Profile.objects.filter(
        canopy_member=True,
    ).order_by("-canopy_karma").values("name", "canopy_karma")

    team_standings = Team.team_points_leaders(num_results=20)

    # Find referrals.
    referrals = Profile.objects.filter(
        referring_user__isnull=False,
    ).values('referring_user__profile__name', 'referring_user__username').annotate(
        referrals=Count('referring_user')
    )

    round_individuals = {}
    round_teams = {}
    for round_name in settings.COMPETITION_ROUNDS:
        round_individuals[round_name] = ScoreboardEntry.objects.filter(
            points__gt=0,
            round_name=round_name,
        ).order_by("-points", "-last_awarded_submission").values("profile__name", "points",
            'profile__user__username')

        round_teams[round_name] = Team.team_points_leaders(
            num_results=20,
            round_name=round_name
        )

    # Calculate active participation.
    team_participation = Team.objects.filter(profile__points__gte=50).annotate(
        user_count=Count('profile'),
    ).order_by('-user_count').select_related('group')

    for team in team_participation:
        team.active_participation = (team.user_count * 100) / team.profile_set.count()

    return render_to_response("status/points.html", {
        "profiles": profiles,
        "canopy_members": canopy_members,
        "round_individuals": round_individuals,
        "team_standings": team_standings,
        "round_teams": round_teams,
        "team_participation": team_participation,
        "referrals": referrals,
        }, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def energy_scoreboard(request):
    goals_scoreboard = TeamEnergyGoal.objects.filter(
        actual_usage__lte=F("goal_usage")
    ).values(
        "team__name",
    ).annotate(completions=Count("team")).order_by("-completions")

    return render_to_response("status/energy.html", {
        "goals_scoreboard": goals_scoreboard,
        }, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def users(request):
    todays_users = Profile.objects.filter(last_visit_date=datetime.datetime.today())

    # Approximate logins by their first points transaction.
    start = datetime.datetime.strptime(settings.COMPETITION_START, "%Y-%m-%d")
    today = datetime.datetime.today()

    users_anno = User.objects.annotate(login_date=Min('pointstransaction__submission_date'))
    logins = []
    while start <= today:
        result = {}
        result['date'] = start.strftime("%m/%d")
        result['logins'] = users_anno.filter(login_date__gte=start,
            login_date__lt=start + datetime.timedelta(days=1)).count()
        logins.append(result)
        start += datetime.timedelta(days=1)

    return render_to_response("status/users.html", {
        "todays_users": todays_users,
        'logins': logins,
        }, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def prizes(request):
    deadlines = RaffleDeadline.objects.all().order_by("pub_date")

    # Calculate unused raffle tickets for every user.
    elig_users = User.objects.filter(profile__points__gte=25).select_related('profile', 'raffleticket')
    unused = 0
    errors = []
    for user in elig_users:
        available = (user.get_profile().points / 25) - user.raffleticket_set.count()
        if available < 0:
            errors.append(user.username)
        unused += available

    return render_to_response("status/prizes.html", {
        "deadlines": deadlines,
        "unused": unused,
        "has_error": len(errors) > 0,
        "errors": errors,
        }, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def popular_activities(request):
    tasks = {}
    types = ActivityBase.objects.values('type').distinct()
    for item in types:
        task_type = item["type"]
        if task_type == 'commitment':
            tasks[task_type] = get_popular_commitments()
        elif task_type == 'event' or task_type == 'excursion':
            tasks[task_type] = get_popular_events(activity_type=task_type)
        else:
            tasks[task_type] = get_popular_activities(activity_type=task_type)

    quests = Quest.objects.filter(
        questmember__completed=True,
    ).values("name").annotate(completions=Count("questmember")).order_by("-completions")

    members = ActivityMember.objects.filter(
        activity__type='activity',
        approval_status='pending',
    ).order_by('submission_date')

    pending_members = members.count()
    oldest_member = None
    if pending_members > 0:
        oldest_member = members[0]

    return render_to_response("status/activities.html", {
        "tasks": tasks,
        "quests": quests,
        "pending_members": pending_members,
        "oldest_member": oldest_member,
        }, context_instance=RequestContext(request))


@user_passes_test(lambda u: u.is_staff, login_url="/account/cas/login")
def event_rsvps(request):
    events = Activity.objects.filter(
        type="event",
        activitymember__approval_status="pending",
    ).annotate(rsvps=Count('activitymember')).order_by('-rsvps')
    excursions = Activity.objects.filter(
        type="excursion",
        activitymember__approval_status="pending",
    ).annotate(rsvps=Count('activitymember')).order_by('-rsvps')

    return render_to_response("status/rsvps.html", {
        "events": events,
        "excursions": excursions,
        }, context_instance=RequestContext(request))
  
  