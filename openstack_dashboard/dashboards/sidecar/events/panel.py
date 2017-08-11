# File Name: panel.py
#
# Software: Openstack Horizon [liberity]
#
# Dashboard Name: Sidecar
#
# Panel Name: events
#
# Start Date: 2016@nephoscale.com

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.sidecar import dashboard
import horizon

class Events(horizon.Panel):
    name = _("Evacuation Events")
    slug = "events"
dashboard.SidecarDashboard.register(Events)
