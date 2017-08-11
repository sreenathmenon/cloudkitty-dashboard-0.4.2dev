# _______________________________________________________________________
# | File Name: views.py                                                 |
# |                                                                     |
# | This file is for handling the views of support ticket display       |
# |_____________________________________________________________________|
# | Start Date: Aug 31th, 2016                                          |
# |                                                                     |
# | Package: Openstack Horizon Dashboard [liberity]                     |
# |                                                                     |
# | Copy Right: 2016@nephoscale                                         |
# |_____________________________________________________________________|

from openstack_dashboard.dashboards.sidecar.events import tabs as event_tabs
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.sidecar.events import tables
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.http import  HttpResponseRedirect
from django.shortcuts import render
from horizon import views
from horizon import tabs
from horizon import exceptions
from horizon.utils import memoized
from django.conf import settings
from sidecarclient import client
import requests
import json

class IndexView(tabs.TabbedTableView):
    """
    # | IndexView for showing ticket list 
    # |
    # | Code is in tabs.py 
    """
    tab_group_class = event_tabs.EvacuationEventsTab
    template_name   = "sidecar_dashboard/events/index.html"
    page_title      = "Evacuation Events"

def get_event_detail(request, **kwargs):

    #Configuring the settings
    #Values are taken from settings.py file
    sidecar = client.Client(
        username = getattr(settings, "SC_USERNAME"),
        password = getattr(settings, "SC_PASSWORD"),
        auth_url = getattr(settings, "SC_AUTH_URL"),
        region_name = getattr(settings, "SC_REGION_NAME"),
        tenant_name = getattr(settings, "SC_TENANT_NAME"),
        timeout = getattr(settings, "SC_TIMEOUT"),
        insecure = getattr(settings, "SC_INSECURE")
    )

    #Fetching the details of the selected event
    event_details = sidecar.events.detail(id=kwargs['event_id'])
    context = {
        "page_title": _("Event Details: %s") %(event_details.name),
        "events": event_details
    }
    return render(request, 'sidecar_dashboard/events/event_detail.html', context)

