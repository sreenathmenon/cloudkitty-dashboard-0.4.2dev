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
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon import views

from cloudkittydashboard.api import cloudkitty as api
from cloudkittydashboard.dashboards.identity.billing import forms as hashmap_forms
from cloudkittydashboard.dashboards.identity.billing \
    import tables as hashmap_tables
import memcache
mc = memcache.Client(['127.0.0.1:11211'], debug=0)

class IndexView(tables.DataTableView):
    table_class = hashmap_tables.ServicesTable
    template_name = "identity/billing/services_list.html"

    def get_data(self):
        out = api.cloudkittyclient(self.request).hashmap.services.list()
 
	#Creating new list
	new_list = []

	#For creating the list	
	for list_index, lists in enumerate(out):
	    
	    #to show only the instance and tenant addon
	    if lists.name == 'instance.addon' or lists.name == 'tenant.addon':

		#Making the field list and passing it to the identify
		field_lists = api.cloudkittyclient(self.request).hashmap.fields.list(service_id=lists.service_id)
		
		#Creating the field list
		for field_list in field_lists:
		    if lists.name == 'instance.addon':	
		  	service_name = 'Instance Add-On'
		    elif lists.name == 'tenant.addon':
			service_name = 'Tenant Add-On'
		    setattr(field_list, 'service_name', service_name)	
		    new_list.append(field_list)
		    	
        return api.identify(new_list)


class ServiceView(tabs.TabbedTableView):
    tab_group_class = hashmap_tables.ServiceTabs
    template_name = 'identity/billing/service_details.html'

    def get(self, *args, **kwargs):
        service = api.cloudkittyclient(self.request).hashmap.services.get(
            service_id=kwargs['service_id']
        )
	
        self.request.service_id = service.service_id
        self.page_title = "Hashmap Service : %s" % service.name
	return super(ServiceView, self).get(*args, **kwargs)

class FieldView(tabs.TabbedTableView):
    tab_group_class = hashmap_tables.FieldTabs
    template_name = 'identity/billing/field_details.html'

    def get(self, *args, **kwargs):
        field = api.cloudkittyclient(self.request).hashmap.fields.get(
            field_id=kwargs['field_id']
        )
	
        self.request.field_id = field.field_id
	if field.name == 'tenant_id':
	    self.page_title = 'Tenant Add-Ons'
	elif field.name == 'instance_id':
            self.page_title = 'Instance Add-Ons'
	else:
            self.page_title = field.name

        mc.set("button_name", self.page_title)
        return super(FieldView, self).get(*args, **kwargs)

class FieldMappingCreateView(forms.ModalFormView):

    form_class = hashmap_forms.CreateFieldMappingForm
    form_id = "create_field_mapping"
    modal_header = _("Create Add-On")
    page_title = _("Create Add-On")
    template_name = 'horizon/common/modal_form.html'
    submit_url = 'horizon:identity:billing:field_mapping_create'
    success_url = 'horizon:identity:billing:field_mapping_create'

    def get_object_id(self, obj):
        return obj.mapping_id

    def get_context_data(self, **kwargs):
        context = super(FieldMappingCreateView,
                        self).get_context_data(**kwargs)
        context["field_id"] = self.kwargs.get('field_id')
        context['submit_url'] = reverse_lazy(self.submit_url,
                                             args=(context['field_id'], ))
        return context

    def get_initial(self):
        return {"field_id": self.kwargs.get("field_id"), 'group_id': self.request.session['group_id']}


    def get_success_url(self, **kwargs):
        return reverse('horizon:identity:billing:field',
                       args=(self.kwargs['field_id'], ))


class FieldMappingEditView(FieldMappingCreateView):
    form_class = hashmap_forms.EditFieldMappingForm
    form_id = "update_field_mapping"
    modal_header = _("Update Add-On")
    page_title = _("Update Add-On")
    submit_url = 'horizon:identity:billing:field_mapping_edit'

    def get_initial(self):
        out = api.cloudkittyclient(self.request).hashmap.mappings.get(
            mapping_id=self.kwargs['mapping_id'])
        self.initial = out.to_dict()
        return self.initial

    def get_context_data(self, **kwargs):
        context = super(FieldMappingEditView,
                        self).get_context_data(**kwargs)
        context["mapping_id"] = self.kwargs.get('mapping_id')
        context['submit_url'] = reverse_lazy(self.submit_url,
                                             args=(context['mapping_id'], ))
        return context

    def get_success_url(self, **kwargs):
        return reverse('horizon:identity:billing:field',
                       args=(self.initial['field_id'], ))

