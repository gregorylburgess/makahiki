"""
main views module to render pages.
"""
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import importlib
from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from apps.managers.settings_mgr.models import PageSettings


@never_cache
def root_index(request):
    """
    hanlde the landing page.
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("home_index"))
    return HttpResponseRedirect(reverse("landing", args=()))


@never_cache
@login_required
def index(request):
    """
    handle dynamically lay-outed pages defined in page_settings.
    """
    page_name = request.path[1:][:-1]

    # get the view_objects
    view_objects = {}
    is_page_defined = _get_view_objects(request, page_name, view_objects)

    if not is_page_defined:
        return HttpResponseRedirect(reverse("home_index"))

    # get user energy rank and usage
    _get_energy_rank(request, view_objects)

    return render_to_response("%s/index.html" % page_name, {
        "view_objects": view_objects,
        }, context_instance=RequestContext(request))


def _get_view_objects(request, page_name, view_objects):
    """ Returns view_objects supplied widgets defined in page_settings.py. """

    page_settings = PageSettings.objects.filter(name=page_name)
    if page_settings.count() == 0:
        return False

    for page_setting in page_settings:
        widget = page_setting.widget
        view_module_name = 'apps.widgets.' + widget + '.views'
        page_views = importlib.import_module(view_module_name)
        view_objects[widget] = page_views.supply(request, page_name)

    return True


def _get_energy_rank(request, view_objects):
    """ Gets the user energy rank and usage."""
    if "widgets.energy_scoreboard" in settings.INSTALLED_WIDGET_APPS:
        module = importlib.import_module("apps.widgets.energy_scoreboard.models")
        energy_rank_info = module.EnergyData.get_team_overall_rank_info(
            request.user.get_profile().team)
        view_objects["energy_rank_info"] = energy_rank_info


def _get_widget_css(view_objects):
    """
    Returns the contents of the available widget css file
    """
    widget_css = ""
    for widget in view_objects.keys():
        widget_css_file = "%s/apps/widgets/%s/templates/css.css" % (
        settings.PROJECT_ROOT, widget)
        try:
            infile = open(widget_css_file)
            widget_css += infile.read() + "\n"
        except IOError:
            pass
    return widget_css