from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from widgets.profile.forms import ProfileForm
from widgets.profile import  get_in_progress_members
from widgets.smartgrid import get_current_commitment_members

from lib.brabeion import badges
from lib.brabeion.models import BadgeAward


def supply(request, page_name):
    user = request.user
    form = None
    if request.method == "POST":
        user = request.user
        form = ProfileForm(request.POST, user=request.user)
        if form.is_valid():
            profile = user.get_profile()
            name = form.cleaned_data["display_name"].strip()

            if name != profile.name:
                profile.name = name

            profile.contact_email = form.cleaned_data["contact_email"]
            profile.contact_text = form.cleaned_data["contact_text"]
            profile.contact_carrier = form.cleaned_data["contact_carrier"]
            # profile.enable_help = form.cleaned_data["enable_help"]

            profile.save()
            form.message = "Your changes have been saved"

        else:
            form.message = "Please correct the errors below."

    # If this is a new request, initialize the form.
    if not form:
        profile = user.get_profile()
        form = ProfileForm(initial={
            # "enable_help": user.get_profile().enable_help,
            "display_name": profile.name,
            "contact_email": profile.contact_email or user.email,
            "contact_text": profile.contact_text,
            "contact_carrier": profile.contact_carrier,
            })

        if request.GET.has_key("changed_avatar"):
            form.message = "Your avatar has been updated."

    points_logs = user.pointstransaction_set.order_by("-submission_date").all()

    return {
        "form": form,
        "in_progress_members": get_in_progress_members(user),
        "commitment_members": get_current_commitment_members(user),
        "points_logs": points_logs,
        # "notifications": user.usernotification_set.order_by("-created_at"),
    }

@login_required
def view_rejected(request, rejected_id):
    request.session["rejected_id"] = rejected_id
    return HttpResponseRedirect(reverse("profile_index"))