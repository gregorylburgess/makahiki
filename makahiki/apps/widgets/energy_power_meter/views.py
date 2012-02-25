import datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from lib.gviz_api import gviz_api
from widgets.energy_power_meter.models import PowerData

def supply(request, page_name):
    return {}

@login_required
def power_data(request):
    user = request.user

    description = {"A": ("string", "Source"),
                   "B": ("date", "Last Update"),
                   "C": ("number", "Current Power"),
                   "D": ("number", "Baseline Power")}

    # Loading it into gviz_api.DataTable
    data_table = gviz_api.DataTable(description)

    try:
        power = PowerData.objects.get(team = user.get_profile().team)
        data = [{"A": power.team.name,
             "B": power.updated_at,
             "C": power.current_power,
             "D": power.baseline_power,
            }]

        data_table.AppendData(data)
    except ObjectDoesNotExist:
        pass

    return HttpResponse(data_table.ToResponse(tqx = "reqId:0"))