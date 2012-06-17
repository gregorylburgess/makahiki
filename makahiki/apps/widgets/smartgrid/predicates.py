"""Predicates indicating the state of the smart grid to determine if a level or cell should be unlocked."""

from apps.widgets.smartgrid.models import Action, Category


def completed_action(user, slug):
    """Returns true if the user complete the action."""
    return user.actionmember_set.filter(action__slug=slug).count() > 0


def completed_all_of(user, category_slug=None, action_type=None, resource=None):
    """Returns true if completed all of specified type."""

    if category_slug:
        return user.actionmember_set.filter(action__category__slug=category_slug).count() ==\
           Category.objects.filter(slug=category_slug).count()

    if action_type:
        return user.actionmember_set.filter(action__type=action_type).count() ==\
            Action.objects.filter(type=action_type).count()

    if resource:
        return user.actionmember_set.filter(action__related_resource=resource).count() ==\
            Action.objects.filter(related_resource=resource).count()

    return user.actionmember_set.all().count() ==\
           Action.objects.all().count()


def completed_some_of(user, some=1, category_slug=None, action_type=None, resource=None):
    """Returns true if completed some of the specified type.
    some is default to 1 if not specified."""
    if category_slug:
        return user.actionmember_set.filter(action__category__slug=category_slug).count() >= some

    if action_type:
        return user.actionmember_set.filter(action__type=action_type).count() >= some

    if resource:
        return user.actionmember_set.filter(action__related_resource=resource).count() >= some

    return user.actionmember_set.all().count() >= some


def approved_action(user, slug):
    """Returns true if the action is approved."""
    return user.actionmember_set.filter(action__slug=slug, approval_status="approved").count() > 0


def approved_some_of(user, some=1, category_slug=None, action_type=None, resource=None):
    """Returns true if some actions of the specified type is approved."""

    if category_slug:
        return user.actionmember_set.filter(action__category__slug=category_slug,
                                            approval_status="approved").count() >= some

    if action_type:
        return user.actionmember_set.filter(action__type=action_type,
                                            approval_status="approved").count() >= some

    if resource:
        return user.actionmember_set.filter(action__related_resource=resource,
                                            approval_status="approved").count() >= some

    return user.actionmember_set.filter(approval_status="approved").count() >= some


def approved_all_of(user, category_slug=None, action_type=None, resource=None):
    """Returns true if all actions of the specified type is approved."""

    if category_slug:
        return user.actionmember_set.filter(action__category__slug=category_slug,
                                            approval_status="approved").count() ==\
               Category.objects.filter(slug=category_slug).count()

    if action_type:
        return user.actionmember_set.filter(action__type=action_type,
                                            approval_status="approved").count() ==\
               Action.objects.filter(type=action_type).count()

    if resource:
        return user.actionmember_set.filter(action__related_resource=resource,
                                            approval_status="approved").count() ==\
               Action.objects.filter(related_resource=resource).count()

    return user.actionmember_set.filter(approval_status="approved").count() ==\
           Action.objects.all().count()
