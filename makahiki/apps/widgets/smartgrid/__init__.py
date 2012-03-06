"""Smartgrid widget."""

import datetime

from django.db.models import Q
from django.conf import settings
from django.db.models import Sum, Count
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.core.cache import cache
from itertools import chain
from operator import attrgetter

from apps.widgets.smartgrid.models import Activity, ActivityBase, Category, Commitment, \
                                          ActivityMember, CommitmentMember

# Directory in which to save image files for ActivityMember verification.
ACTIVITY_FILE_DIR = getattr(settings, 'ACTIVITY_FILE_DIR', 'activities')

# Maximum number of commitments user can have at one time.
MAX_COMMITMENTS = 5


def get_popular_tasks():
    """
    Returns a dictionary containing the most popular tasks.
    The keys are the type of the task and the values are a list of tasks.
    """
    return {
        "Activity": get_popular_activities("activity")[:5],
        "Commitment": get_popular_commitments()[:5],
        "Event": get_popular_events("event")[:5],
        "Excursion": get_popular_events("excursion")[:5],
        }


def get_popular_activities(activity_type="activity"):
    """Gets the most popular activities in terms of completions."""
    return Activity.objects.filter(
        activitymember__approval_status="approved",
        type=activity_type,
    ).values("title", "type", "slug").annotate(completions=Count("activitymember")).order_by(
        "-completions")


def get_popular_events(activity_type='event'):
    """Returns popular events."""
    if activity_type == 'event' or activity_type == 'excursion':
        return Activity.objects.filter(
            activitymember__approval_status="pending",
            type=activity_type,
        ).values("title", "type", "slug").annotate(completions=Count("activitymember")).order_by(
            "-completions")
    return None


def get_popular_commitments():
    """Gets the most popular commitments in terms of completions."""
    return Commitment.objects.filter(
        commitmentmember__award_date__isnull=False,
    ).values("title", "type", "slug").annotate(completions=Count("commitmentmember")).order_by(
        "-completions")


def get_incomplete_tasks(user):
    """Gets user's incomplete activities and commitments. Returns a dictionary."""

    user_commitments = get_current_commitments(user)
    user_activities = get_current_activities(user)

    return {
        "commitments": user_commitments,
        "activities": user_activities,
        }


def get_incomplete_task_members(user):
    """Gets user's incomplete activity and commitment members."""
    commitment_members = get_current_commitment_members(user)
    activity_members = get_current_activity_members(user)

    return {
        "commitments": commitment_members,
        "activities": activity_members,
        }


def is_pending_commitment(user, commitment):
    """check if the commitment is pending."""
    return CommitmentMember.objects.filter(user=user, commitment=commitment, award_date=None)


def can_add_commitments(user):
    """Determines if the user can add additional commitments."""
    return CommitmentMember.objects.filter(user=user,
        award_date__isnull=True).count() < MAX_COMMITMENTS


def can_complete_commitments(user, commitment):
    """Determines if the user can complete commitments, assuming there is a pending commitment"""
    members = CommitmentMember.objects.filter(user=user,
                                             commitment=commitment,
                                             award_date=None)
    if members:
        return members[0].days_left() == 0
    else:
        return False


def get_current_commitments(user):
    """Get the user's incomplete commitments."""
    return user.commitment_set.filter(
        commitmentmember__award_date=None,
    ).order_by("commitmentmember__completion_date")


def get_current_commitment_members(user):
    """Get the user's membership objects in the incomplete commitments."""
    return user.commitmentmember_set.filter(
        award_date=None
    ).order_by("completion_date")


def get_available_commitments(user):
    """Get any commitments that the user is not currently active in."""
    return Commitment.objects.exclude(
        id__in=get_current_commitments(user),
    ).order_by("title")


def get_completed_commitments(user):
    """Gets the user's completed commitments"""
    return user.commitment_set.filter(
        commitmentmember__award_date__isnull=False,
    ).order_by("title")


def get_current_activities(user):
    """Get the user's incomplete activities."""

    return user.activity_set.filter(
        activitymember__award_date=None,
    ).order_by("activitymember__submission_date")


def get_current_activity_members(user):
    """Get the user's incomplete activity members."""
    return user.activitymember_set.exclude(
        activity__type="survey",
    ).filter(
        award_date=None,
    ).order_by("submission_date")


def get_available_activities(user):
    """Retrieves only the activities that a user can participate in (excluding events)."""

    activities = Activity.objects.exclude(
        activitymember__user=user,
    ).filter(
        type='activity',
        pub_date__lte=datetime.date.today(),
        expire_date__gte=datetime.date.today(),
    ).order_by("priority", "title")

    return activities


def get_available_golow_activities(user):
    """Retrieves only the golow activities that a user can participate in (excluding events)."""

    commitments = Commitment.objects.exclude(
        commitmentmember__user=user,
    ).filter(
        energy_related=True,
        is_canopy=False,
    ).order_by("priority").values("id", "depends_on", "type", "slug", "title", "point_value")

    golow_tasks = []
    for task in commitments:
        if is_unlock_by_id(user, task["id"], task["depends_on"], None, None):
            golow_tasks.append(task)
            break

    activities = Activity.objects.exclude(
        activitymember__user=user,
    ).filter(
        energy_related=True,
        pub_date__lte=datetime.date.today(),
        expire_date__gte=datetime.date.today(),
        is_canopy=False,
    ).order_by("type", "priority").values("id", "depends_on", "type", "slug", "title",
                                          "point_value", "point_range_end")

    _pick_one_activity_per_type(user, activities, golow_tasks)

    if len(golow_tasks) < 3:
        _pick_one_activity_per_type(user, activities, golow_tasks)

    return golow_tasks


def _pick_one_activity_per_type(user, activities, golow_tasks):
    """return one activity per type. """
    activity_type = None
    for task in activities:
        if task in golow_tasks:
            continue

        if activity_type == task["type"]:
            continue

        if is_unlock_by_id(user, task["id"], task["depends_on"], None, None):
            golow_tasks.append(task)
            activity_type = task["type"]

            if len(golow_tasks) == 3:
                break


def get_available_events(user):
    """Retrieves only the events that a user can participate in."""

    events = Activity.objects.filter(
        Q(type='event') | Q(type='excursion'),
        pub_date__lte=datetime.date.today(),
        expire_date__gte=datetime.date.today(),
        event_date__gte=datetime.date.today(),
        is_canopy=False,
    ).order_by("event_date").values("id", "depends_on", "type", "slug", "title", "point_value",
        "event_date", "event_location")

    unlock_events = []
    for event in events:
        if is_unlock_by_id(user, event["id"], event["depends_on"], None, None):
            if not ActivityMember.objects.filter(user=user, activity__id=event["id"],
                award_date__isnull=False):
                unlock_events.append(event)

    return unlock_events  # Filters out inactive activities.


def get_completed_activities(user):
    """Gets the user's completed activities"""
    return user.activity_set.filter(
        activitymember__award_date__isnull=False,
    ).order_by("title")


def get_completed_tasks(user, category):
    """Gets the user's completed tasks by category"""
    return Activity.objects.filter(activitymember__user=user,
        category=category).count() + Commitment.objects.filter(commitmentmember__user=user,
        category=category).count()


def get_awarded_points(user, category):
    """Gets the user's awarded points by category"""
    asum = Activity.objects.filter(activitymember__user=user, category=category).aggregate(
        Sum('point_value'))
    apoint = asum['point_value__sum']
    if apoint == None:
        apoint = 0
    csum = Commitment.objects.filter(commitmentmember__user=user, category=category).aggregate(
        Sum('point_value'))
    cpoint = csum['point_value__sum']
    if cpoint == None:
        cpoint = 0
    return 0 + apoint + cpoint


def is_pau(user, task):
    """return true if the task is done for the user."""
    return is_pau_by_id(user, task.id, task.type)


def is_pau_by_id(user, task_id, task_type):
    """return true if the task specified by the task_id is done for the user."""
    if task_type != "commitment":
        pau = ActivityMember.objects.filter(user=user, activity__id=task_id).count() > 0
    else:
        pau = CommitmentMember.objects.filter(user=user, commitment__id=task_id).count() > 0
    return pau


def completedAllOf(user, cat_slug):
    """completed all of the category"""
    try:
        cat = Category.objects.get(slug=cat_slug)
    except ObjectDoesNotExist:
        return False

    for task in cat.activitybase_set.all():
        if is_pau(user, task) != True:
            return False

    return True


def completedSomeOf(user, some, cat_slug):
    """completed some of the category"""
    try:
        cat = Category.objects.get(slug=cat_slug)
    except ObjectDoesNotExist:
        return False

    count = 0
    for task in cat.activitybase_set.all():
        if is_pau(user, task):
            count = count + 1
        if count == some:
            return True

    return False


def completed(user, activity_members, commitment_members, task_slug):
    """completed the task"""

    if activity_members != None:
        for member in activity_members:
            if member["slug"] == task_slug:
                return True

        for member in commitment_members:
            if member["slug"] == task_slug:
                return True
    else:
        try:
            task = ActivityBase.objects.get(slug=task_slug)
        except ObjectDoesNotExist:
            return False

        return is_pau(user, task)


def afterPublished(task_id):
    """return true if the event/excursion have been published"""
    try:
        return Activity.objects.get(id=task_id).pub_date <= datetime.date.today()
    except ObjectDoesNotExist:
        return False


def is_unlock_from_cache(user, task):
    """check the unlocking of a task from cache."""
    if task.is_canopy:
        return is_unlock(user, task)

    categories = cache.get('smartgrid-categories-%s' % user.username)
    if not categories:
        return is_unlock(user, task)

    for cat in categories:
        if cat.id == task.category_id:
            for t in cat.task_list:
                if t["id"] == task.id:
                    return t["is_unlock"]


def is_unlock(user, task):
    """determine the unlock status of a task by dependency expression"""

    # only canopy member able to see canopy activity
    profile = user.get_profile()

    if task.is_canopy and profile != None and not profile.canopy_member:
        return False

    return is_unlock_by_id(user, task.id, task.depends_on, None, None)


def is_unlock_by_id(user, task_id, task_depends_on, activity_members, commitment_members):
    """check the unlocking by the task_id."""
    expr = task_depends_on
    if expr == None or expr == "":
        return False

    expr = expr.replace("completedAllOf(", "completedAllOf(user,")
    expr = expr.replace("completedSomeOf(", "completedSomeOf(user,")
    expr = expr.replace("completed(", "completed(user,activity_members,commitment_members,")
    expr = expr.replace("afterPublished(", "afterPublished(%d" % (task_id))

    allow_dict = {'completedAllOf': completedAllOf,
                  'completedSomeOf': completedSomeOf,
                  'completed': completed,
                  'afterPublished': afterPublished,
                  'True': True,
                  'False': False,
                  'user': user,
                  'activity_members': activity_members,
                  'commitment_members': commitment_members,
                  }

    return eval(expr, {"__builtins__": None}, allow_dict)


def annotate_task_status(user, task):
    """Adds additional fields that identify whether or not the activity is approved."""
    task.is_unlock = is_unlock(user, task)
    task.is_pau = is_pau(user, task)
    if task.type == "event" or task.type == "excursion":
        task.is_event_pau = Activity.objects.get(pk=task.pk).is_event_completed()

    members = None
    if task.type != "commitment":
        members = ActivityMember.objects.filter(user=user, activity=task).order_by("-updated_at")
    else:
        members = CommitmentMember.objects.filter(user=user, commitment=task)

    if members.count() > 0:
        task.approval = members[0]

    return task


def _get_task_members(task, activity_members, commitment_members):
    """check the task is in members list"""

    if task["type"] != "commitment":
        for member in activity_members:
            if member["activity_id"] == task["id"]:
                return member
    else:
        for member in commitment_members:
            if member["commitment_id"] == task["id"]:
                return member


def annotate_simple_task_status(user, task, activity_members, commitment_members):
    """Adds additional fields that identify whether or not the activity is approved."""

    has_member = _get_task_members(task, activity_members, commitment_members)
    if has_member:
        task["is_pau"] = True
        task["is_unlock"] = True
        task["approval"] = has_member
        if task["type"] == "commitment":
            diff = task["approval"]["completion_date"] - datetime.date.today()
            if diff.days < 0:
                task["approval"]["days_left"] = 0
            else:
                task["approval"]["days_left"] = diff.days
            task["point_value"] = task["commitment_point_value"]
        else:
            task["point_value"] = task["activity_point_value"]
            if task["event_date"]:
                result = datetime.datetime.today() - task["event_date"]
                if result.days >= 0 and result.seconds >= 0:
                    task["is_event_pau"] = True
                else:
                    task["is_event_pau"] = False
    else:
        task["is_pau"] = False
        task["is_unlock"] = is_unlock_by_id(user, task["id"], task["depends_on"], activity_members,
            commitment_members)
        if task["is_unlock"]:
            if task["type"] == "commitment":
                task["point_value"] = task["commitment_point_value"]
            else:
                task["point_value"] = task["activity_point_value"]

    return task


def get_user_by_email(email):
    """return the user from given email"""
    try:
        return User.objects.get(email=email)
    except ObjectDoesNotExist:
        return None


def get_completed_members(user):
    """ Retrieve previously awarded tasks, quests, and badges.
    Note that we need to check the various activity types because of signup bonuses.
    """
    activity_members = user.activitymember_set.exclude(
        activity__type="activity",
        award_date__isnull=True,
        ).exclude(
        activity__type="survey",
        approval_status="pending",
        )

    commitment_members = user.commitmentmember_set.all()
    quest_members = user.questmember_set.filter(completed=True)
    badge_members = user.badges_earned.all()

    for member in badge_members:
        member.updated_at = member.awarded_at

    # Merge the querysets, sort according to award_date, and take 5
    # Solution found at:
    # http://stackoverflow.com/questions/431628/how-to-combine-2-or-more-querysets-in-a-django-view
    return sorted(
        chain(activity_members, commitment_members, quest_members, badge_members),
        key=attrgetter("updated_at"), reverse=True)


def get_in_progress_members(user):
    """Retrieve current tasks."""
    in_progress_activity_members = get_current_activity_members(user)
    in_progress_commitment_members = get_current_commitment_members(user)
    return sorted(
        chain(in_progress_activity_members, in_progress_commitment_members),
        key=attrgetter("created_at"), reverse=True)
