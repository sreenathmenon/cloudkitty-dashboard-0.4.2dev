# File Name: tables.py
#
# Package Name: Openstack Horizon [liberity]
#
# Dashboardd: Sidecar
#
# Start Date: Aug 31th, 2016
#
# Copyright: 2016@nephoscale.com
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from django.core.urlresolvers import reverse, reverse_lazy

class EventFilterAction(tables.FilterAction):
    """
    # | Class to filtering the events
    """
    name = "eventfilter"
    filter_type = "server"
    verbose_name = _("Filter Events")
    needs_preloading = True
    filter_choices = (("id", _("ID"), True),
                     ("name", _("Name"), True),
                     ("event_status", _("Event Status"), True),
                     ("node_uuid", _("Node UUID"), True),
                     ('event_create_time', _("Create Time >="), True),
                     ('vm_uuid_list', _("VM UUID"), True))

def transform_status(event):
    """
    # | Function to transform the status to uppercase
    # | 
    # | Event object
    # |
    # | Returns string
    """

    if not event.event_status:
        return '-'
    return str(event.event_status).upper()

class EventListTable(tables.DataTable):
    """ 
    TABLE TO LIST THE EVENTS
    """
    name = tables.Column('name', verbose_name=_('Name'), sortable=True, link='horizon:sidecar_dashboard:events:event_detail')
    status = tables.Column('event_status', verbose_name=_("Status"), sortable=True)
    #transform_status
    status = tables.Column(transform_status, verbose_name=_("Status"), sortable=True)
    node_uuid   = tables.Column('node_uuid',   verbose_name=_("Node UUID"), sortable=True)
    event_create_time  = tables.Column('event_create_time', verbose_name=_('Created Time'), sortable=True)
    last_update    = tables.Column('event_complete_time', verbose_name=_("Last Updated"), sortable=True)
     
    class Meta:
        name = "events"
        verbose_name = _("Evacuation Events")
        table_actions = ()
        table_actions = (EventFilterAction,)

class LogListTable(tables.DataTable):
    """ 
    TABLE TO LIST THE LOGS
    """
    hypervisor_name = tables.Column('hypervisor_name', verbose_name=_('Hypervisor Name'), sortable=True)
    down_since = tables.Column('down_since', verbose_name=_("Down Since"), sortable=True)
    event_creation_time  = tables.Column('event_creation_time', verbose_name=_('Created Time'), sortable=True)

    class Meta:
        name = "logs"
        verbose_name = _("Evacuate Event Logs")
        table_actions = ()
