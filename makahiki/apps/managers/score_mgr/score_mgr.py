"""The manager for defining and managing scores."""
import datetime

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.aggregates import Sum, Max
from apps.managers.challenge_mgr import challenge_mgr
from apps.managers.score_mgr.models import ScoreboardEntry, PointsTransaction, ScoreSetting
from apps.managers.cache_mgr import cache_mgr


def info():
    """returns the score_mgr info."""
    s = score_setting()
    return  "referral_points: %d \n" \
            "signup_points: %d \n" \
            "setup_points: %d \n" \
            "noshow_penalty_points: %d \n" \
            "quest_points: %d" % (s.referral_bonus_points, s.signup_bonus_points,
                                s.setup_points, s.noshow_penalty_points, s.quest_bonus_points)


def score_setting():
    """returns the score settings."""
    score = cache_mgr.get_cache('score_setting')
    if not score:
        score, _ = ScoreSetting.objects.get_or_create(pk=1)
        cache_mgr.set_cache('score_setting', score, 2592000)
    return score


def referral_points():
    """returns the referral point amount from settings."""
    return score_setting().referral_bonus_points


def active_threshold_points():
    """returns the referral point amount from settings."""
    return score_setting().active_threshold_points


def setup_points():
    """returns the setup point amount from settings."""
    return score_setting().setup_points


def signup_points():
    """returns the signup point amount from settings."""
    return score_setting().signup_bonus_points


def noshow_penalty_points():
    """returns the noshow penalty point amount from settings."""
    return score_setting().noshow_penalty_points


def quest_points():
    """returns the signup point amount from settings."""
    return score_setting().quest_bonus_points


def feedback_points():
    """returns the action feedback point amount from settings."""
    return score_setting().feedback_bonus_points


def player_rank(profile, round_name=None):
    """user round overall rank"""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entry = None
    try:
        entry = ScoreboardEntry.objects.get(profile=profile, round_name=round_name)
    except ObjectDoesNotExist:
        pass

    # Check if the user has done anything.
    if entry and entry.last_awarded_submission:
        return ScoreboardEntry.objects.filter(
            Q(points__gt=entry.points) |
            Q(points=entry.points,
              last_awarded_submission__gt=entry.last_awarded_submission),
            round_name=round_name,
            ).count() + 1

    if entry:
        points = entry.points
    else:
        points = 0

    # Users who have not done anything yet are assumed to be last.
    return ScoreboardEntry.objects.filter(
        points__gt=points,
        round_name=round_name,
        ).count() + 1


def player_rank_in_team(profile, round_name=None):
    """Returns user's rank in his team."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    team = profile.team
    entry = None
    try:
        entry = ScoreboardEntry.objects.get(profile=profile, round_name=round_name)
    except ObjectDoesNotExist:
        pass

    if entry and entry.last_awarded_submission:
        return ScoreboardEntry.objects.filter(
            Q(points__gt=entry.points) |
            Q(points=entry.points,
              last_awarded_submission__gt=entry.last_awarded_submission),
            profile__team=team,
            round_name=round_name,
            ).count() + 1

    if entry:
        points = entry.points
    else:
        points = 0

    return ScoreboardEntry.objects.filter(
        points__gt=points,
        profile__team=team,
        round_name=round_name,
        ).count() + 1


def player_points(profile, round_name=None):
    """Returns the amount of points the user has in the round."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entry = ScoreboardEntry.objects.filter(profile=profile, round_name=round_name)
    if entry:
        return entry[0].points
    else:
        return 0


def player_points_leader(round_name=None):
    """Returns the points leader (the first place) out of all users, as a Profile object."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entries = ScoreboardEntry.objects.filter(round_name=round_name,).order_by(
        "-points",
        "-last_awarded_submission")
    if entries:
        return entries[0].profile
    else:
        return None


def player_points_leaders(num_results=None, round_name=None):
    """Returns the points leaders out of all users, as a dictionary object
    with profile__name and points.
    """
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entries = ScoreboardEntry.objects.filter(round_name=round_name,).order_by(
        "-points",
        "-last_awarded_submission").values('profile', 'profile__name', 'points')
    if entries:
        if num_results:
            entries = entries[:num_results]
        return entries
    else:
        return None


def player_last_awarded_submission(profile):
    """Returns the last awarded submission date for the profile."""
    entry = profile.scoreboardentry_set.order_by("-last_awarded_submission")
    if entry:
        return entry[0].last_awarded_submission
    else:
        return None


def player_add_points(profile, points, transaction_date, message, related_object=None):
    """Adds points based on the point value of the submitted object."""
    # Create a transaction first.
    transaction = PointsTransaction(
        user=profile.user,
        points=points,
        transaction_date=transaction_date,
        message=message,
        )
    if related_object:
        transaction.related_object = related_object

    transaction.save()

    # update the scoreboard entry
    _update_scoreboard_entry(profile, points, transaction_date)

    # Invalidate info bar cache.
    cache_mgr.invalidate_template_cache("RIB", profile.user.username)


def player_remove_points(profile, points, transaction_date, message, related_object=None):
    """Removes points from the user.
    If the submission date is the same as the last_awarded_submission
    field, we rollback to a previously completed task.
    """

    # update the scoreboard entry
    _update_scoreboard_entry(profile, points * -1, transaction_date)

    # Log the transaction.
    transaction = PointsTransaction(
        user=profile.user,
        points=points * -1,
        transaction_date=transaction_date,
        message=message,
        )
    if related_object:
        transaction.related_object = related_object
    transaction.save()

    # Invalidate info bar cache.
    cache_mgr.invalidate_template_cache("RIB", profile.user.username)


def player_remove_related_points(profile, related_object):
    """Removes all points transaction related to the related_object."""
    txns = related_object.pointstransactions.all()
    points = 0
    last_awarded_submission = None
    for txn in txns:
        points += txn.points
        # find the latest transaction date
        if not last_awarded_submission or (
            txn.points > 0 and last_awarded_submission < txn.transaction_date):
            last_awarded_submission = txn.transaction_date
        txn.delete()

    if last_awarded_submission:
        _update_scoreboard_entry(profile, points * -1, last_awarded_submission)


def _update_scoreboard_entry(profile, points, transaction_date):
    """Update the scoreboard entry for the associated round."""

    current_round = challenge_mgr.get_round_name(transaction_date)
    _update_round_scoreboard_entry(profile, current_round, points, transaction_date)


def _update_round_scoreboard_entry(profile, round_name, points, transaction_date):
    """update the round scoreboard entry for the transaction."""
    entry, _ = ScoreboardEntry.objects.get_or_create(profile=profile, round_name=round_name)
    entry.points += points

    # update the last_awarded_submission
    if points > 0:
        if not entry.last_awarded_submission or transaction_date > entry.last_awarded_submission:
            entry.last_awarded_submission = transaction_date
    else:
        if entry.last_awarded_submission == transaction_date:
            # Need to find the previous update.
            entry.last_awarded_submission = _last_submitted_before(profile.user, transaction_date)

    entry.save()


def _last_submitted_before(user, transaction_date):
    """Time of the last task that was completed before the submission date.
       :returns None if there are no other tasks.
    """
    try:
        return PointsTransaction.objects.filter(
            user=user,
            transaction_date__lt=transaction_date).latest("transaction_date").transaction_date
    except ObjectDoesNotExist:
        return None


def player_has_points(profile, points, round_name=None):
    """Returns True if the user has at least the requested number of points."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entry = ScoreboardEntry.objects.filter(profile=profile, round_name=round_name)
    if entry:
        return entry[0].points >= points
    else:
        return False


def player_points_leaders_in_team(team, num_results=None, round_name=None):
    """Gets the individual points leaders for the team, as Profile objects"""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    results = team.profile_set.select_related('scoreboardentry').filter(
        scoreboardentry__round_name=round_name
    ).order_by("-scoreboardentry__points",
               "-scoreboardentry__last_awarded_submission", )
    if num_results:
        results = results[:num_results]
    return results


def team_rank(team, round_name=None):
    """Returns the rank of the team across all groups."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    aggregate = ScoreboardEntry.objects.filter(
        profile__team=team,
        round_name=round_name).aggregate(points=Sum("points"), last=Max("last_awarded_submission"))

    points = aggregate["points"] or 0
    last_awarded_submission = aggregate["last"]
    # Group by teams, filter out other rounds, and annotate.
    annotated_teams = ScoreboardEntry.objects.values("profile__team").filter(
        round_name=round_name).annotate(team_points=Sum("points"),
                                        last_awarded=Max("last_awarded_submission"))

    count = annotated_teams.filter(team_points__gt=points).count()
    # If there was a submission, tack that on to the count.
    if last_awarded_submission:
        count = count + annotated_teams.filter(
            team_points=points,
            last_awarded_submission__gt=last_awarded_submission
        ).count()

    return count + 1


def team_points(team, round_name=None):
    """Returns the total number of points for the team.  Optional parameter for a round."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    dictionary = ScoreboardEntry.objects.filter(profile__team=team,
                                                round_name=round_name).aggregate(Sum("points"))
    return dictionary["points__sum"] or 0


def team_points_leader(round_name=None):
    """Returns the team points leader (the first place) across all groups, as a Team ID."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entry = ScoreboardEntry.objects.values("profile__team").filter(round_name=round_name).annotate(
        points=Sum("points"),
        last=Max("last_awarded_submission")).order_by("-points", "-last")
    if entry:
        return entry[0]["profile__team"]
    else:
        return None


def team_points_leaders(num_results=None, round_name=None):
    """Returns the team points leaders across all groups, as a dictionary profile__team__name
    and points.
    """
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    entries = ScoreboardEntry.objects.filter(
        round_name=round_name, profile__team__isnull=False).values(
        "profile__team__name").annotate(
            points=Sum("points"),
            last=Max("last_awarded_submission")).order_by("-points", "-last")
    if entries:
        if num_results:
            entries = entries[:num_results]
        return entries
    else:
        return None


def team_points_leaders_in_group(group, num_results=None, round_name=None):
    """Returns the top points leaders for the given group."""
    if not round_name:
        round_name = challenge_mgr.get_round_name()

    results = group.team_set.filter(
        profile__scoreboardentry__round_name=round_name).annotate(
        points=Sum("profile__scoreboardentry__points"),
        last=Max("profile__scoreboardentry__last_awarded_submission")).order_by(
        "-points", "-last")
    if num_results:
        results = results[:num_results]
    return results


def award_referral_bonus(instance, referrer):
    """award the referral bonus to both party."""
    points = referral_points()
    player_add_points(instance, points, datetime.datetime.today(),
                                      'Referred by %s' % referrer.name, instance)
    player_add_points(referrer, points, datetime.datetime.today(),
                      'Referred %s' % instance.name, referrer)
