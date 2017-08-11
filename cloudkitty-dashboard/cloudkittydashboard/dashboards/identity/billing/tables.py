# Copyright 2015 Objectif Libre
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from horizon import tabs
from openstack_dashboard import api as open_api
from openstack_dashboard.api import keystone
from cloudkittydashboard.api import cloudkitty as api
import memcache
mc = memcache.Client(['127.0.0.1:11211'], debug=0)

class ServicesTable(tables.DataTable):
    """This table list the available services.

    Clicking on a service name sends you to a ServiceTabs page.
    """
    name = tables.Column('service_name', verbose_name=_("Name"), link='horizon:identity:billing:field')
    service_id = tables.Column('service_id', verbose_name=_("service id"), link='horizon:identity:billing:field')

    class Meta(object):
        name = "services"
        verbose_name = _(" Billing Add-Ons")
        #table_actions = (CreateService, DeleteService)
        #row_actions = (DeleteService,)

class DeleteField(tables.DeleteAction):
    name = "deletefield"
    verbose_name = _("Delete Field")
    action_present = _("Delete")
    action_past = _("Deleted")
    data_type_singular = _("Field")
    data_type_plural = _("Fields")
    icon = "remove"

    def action(self, request, field_id):
        api.cloudkittyclient(request).hashmap.fields.delete(
            field_id=field_id)


class CreateField(tables.LinkAction):
    name = "createfield"
    verbose_name = _("Create new Field")
    icon = "create"
    ajax = True
    classes = ("ajax-modal",)

    def get_link_url(self, datum=None):
        url = 'horizon:identity:billing:field_create'
        service_id = self.table.request.service_id
        return reverse(url, args=[service_id])


class FieldsTable(tables.DataTable):
    """This table lists the available fields for a given service.

    Clicking on a fields sends you to a MappingsTable.
    """
    name = tables.Column(
        'name',
        verbose_name=_("Name"),
        link='horizon:identity:billing:field')

    class Meta(object):
        name = "fields"
        verbose_name = _("Fields")
        multi_select = False
        row_actions = (DeleteField,)
        table_actions = (CreateField, DeleteField)


class FieldsTab(tabs.TableTab):
    name = _("Fields")
    slug = "hashmap_fields"
    table_classes = (FieldsTable,)
    template_name = "horizon/common/_detail_table.html"
    preload = True

    def get_fields_data(self):
        client = api.cloudkittyclient(self.request)
        fields = client.hashmap.fields.list(service_id=self.request.service_id)
        return api.identify(fields)


class DeleteMapping(tables.DeleteAction):
    name = "deletemapping"
    verbose_name = _("Delete")
    action_present = _("Delete")
    action_past = _("Deleted")
    data_type_singular = _("Mapping")
    data_type_plural = _("Mappings")
    icon = "remove"

    def action(self, request, mapping_id):
        api.cloudkittyclient(request).hashmap.mappings.delete(
            mapping_id=mapping_id)

class BaseMappingsTable(tables.DataTable):
    name = tables.Column('service_header', verbose_name=_("Name"))
    type = tables.Column('service_name', verbose_name=_("Type"))
    cost = tables.Column('cost', verbose_name=_("Cost"))

class ServiceMappingsTable(BaseMappingsTable):

    class Meta(object):
        name = "mappings"
        verbose_name = _("Mappings")
        #row_actions = (EditServiceMapping, DeleteMapping)
        #table_actions = (CreateServiceMapping, DeleteMapping)


class CreateFieldMapping(tables.LinkAction):

    name = "createfieldmapping"
    if mc.get("button_name") == None:
	verbose_name = _("button_name")
    else:
	verbose_name = _( mc.get("button_name"))

    icon = "create"
    ajax = True
    classes = ("ajax-modal",)

    def get_link_url(self, datum=None):
        url = 'horizon:identity:billing:field_mapping_create'
        field_id = self.table.request.field_id
        return reverse(url, args=[field_id])

class EditFieldMapping(tables.LinkAction):
    name = "editfieldmapping"
    verbose_name = _("Edit")
    icon = "edit"
    ajax = True
    classes = ("ajax-modal",)

    def get_link_url(self, datum=None):
        url = 'horizon:identity:billing:field_mapping_edit'
        return reverse(url, args=[datum.mapping_id])


class FieldMappingsTable(BaseMappingsTable):
    value = tables.Column('value', attrs={"id": "service_id"}, verbose_name=_(mc.get("button_name")))

    class Meta(object):
        name = "mappings"
        verbose_name = _("Mappings")
        row_actions = (EditFieldMapping, DeleteMapping)
        table_actions = (CreateFieldMapping, DeleteMapping)


class FieldMappingsTab(tabs.TableTab):
    name = _("Field Mappings")
    slug = "hashmap_field_mappings"
    table_classes = (FieldMappingsTable,)
    template_name = "horizon/common/_detail_table.html"
    preload = True

    def get_mappings_data(self):
        client = api.cloudkittyclient(self.request)
        mappings = client.hashmap.mappings.list(
            field_id=self.request.field_id)
	test_list = []

	for mapp in mappings:
  	    group = api.cloudkittyclient(self.request).hashmap.groups.get(group_id=mapp.group_id)

	    try:
		if 'instance' in group.name:
		    instances = open_api.nova.server_get(self.request, mapp.value)
    		    setattr(mapp, 'service_header', instances.name)
	        else:
		    tenant =  open_api.keystone.tenant_get(self.request, mapp.value, admin=True)
		    setattr(mapp, 'service_header', tenant.name)
	    except Exception as e:
		setattr(mapp, 'service_header', e)

	    setattr(mapp, 'service_name', group.name)
	    test_list.append(mapp)
	    self.request.session['group_id'] = mapp.group_id
        return api.identify(test_list)

class MappingsTab(tabs.TableTab):
    name = _("Service Mappings")
    slug = "hashmap_mappings"
    table_classes = (ServiceMappingsTable,)
    template_name = "horizon/common/_detail_table.html"
    preload = True

    def get_mappings_data(self):
        client = api.cloudkittyclient(self.request)
        mappings = client.hashmap.mappings.list(
            service_id=self.request.service_id)
        return api.identify(mappings)


class FieldTabs(tabs.TabGroup):
    slug = "field_tabs"
    tabs = (FieldMappingsTab,)
    sticky = True

class ServiceTabs(tabs.TabGroup):
    slug = "services_tabs"
    #tabs = (FieldsTab, MappingsTab, GroupsTab)
    tabs = (FieldsTab, MappingsTab)
    sticky = True
