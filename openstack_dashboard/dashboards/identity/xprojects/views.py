# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
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
from django.views import generic

from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import memoized
from horizon.utils import functions as utils
from horizon import workflows
from horizon import forms

from openstack_dashboard import api
from openstack_dashboard.api import keystone
from openstack_dashboard import policy
from openstack_dashboard import usage
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.identity.xprojects \
    import forms as project_forms
from openstack_dashboard.dashboards.identity.xprojects \
    import tables as project_tables
from openstack_dashboard.dashboards.identity.xprojects \
    import workflows as project_workflows
from openstack_dashboard.dashboards.project.overview \
    import views as project_views

from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient
from openstack_dashboard.dashboards.identity.xprojects.tools import is_billing_admin

from openstack_dashboard.dashboards.identity.xprojects.cipher import decrypt
from openstack_dashboard.local.local_settings import CIPHER_KEY, BILLING_ADMIN_ROLE

PROJECT_INFO_FIELDS = ("domain_id",
                       "domain_name",
                       "name",
                       "description",
                       "enabled")

INDEX_URL = "horizon:identity:xprojects:index"


class TenantContextMixin(object):
    @memoized.memoized_method
    def get_object(self):
        tenant_id = self.kwargs['tenant_id']
        try:
            return api.keystone.tenant_get(self.request, tenant_id, admin=True)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project information.'),
                              redirect=reverse(INDEX_URL))

    def get_context_data(self, **kwargs):
        context = super(TenantContextMixin, self).get_context_data(**kwargs)
        context['tenant'] = self.get_object()
        return context


class IndexView(tables.DataTableView):
    table_class = project_tables.TenantsTable
    template_name = 'identity/xprojects/index.html'
    page_title = _("Projects")

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        tenants = []
        marker = self.request.GET.get(
            project_tables.TenantsTable._meta.pagination_param, None)
        domain_context = self.request.session.get('domain_context', None)

        if is_billing_admin(self.request):
            page_size = utils.get_page_size(self.request)

            limit = page_size + 1
            self._more = False

            ks = get_admin_ksclient()
            if hasattr(ks, 'projects'):
                domain = self.request.user.domain_id
                tenants = ks.projects.list(domain=domain, limit=limit, marker=marker)
            else:
                tenants = ks.tenants.list(limit, marker)
            if len(tenants) > page_size:
                tenants.pop(-1)
                self._more = True

        elif policy.check((("identity", "identity:list_projects"),),
                        self.request):
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    domain=domain_context,
                    paginate=True,
                    marker=marker)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project list."))

        elif policy.check((("identity", "identity:list_user_projects"),),
                          self.request):
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    user=self.request.user.id,
                    paginate=True,
                    marker=marker,
                    admin=False)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project information."))
        else:
            msg = \
                _("Insufficient privilege level to view project information.")
            messages.info(self.request, msg)
        return tenants


class ProjectUsageView(usage.UsageView):
    table_class = usage.ProjectUsageTable
    usage_class = usage.ProjectUsage
    template_name = 'identity/xprojects/usage.html'
    csv_response_class = project_views.ProjectUsageCsvRenderer
    csv_template_name = 'project/overview/usage.csv'
    page_title = _("Project Usage")

    def get_data(self):
        super(ProjectUsageView, self).get_data()
        return self.usage.get_instances()


class CreateProjectView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateProject

    def get_initial(self):
        initial = super(CreateProjectView, self).get_initial()

        # Set the domain of the project
        domain = api.keystone.get_default_domain(self.request)
        initial["domain_id"] = domain.id
        initial["domain_name"] = domain.name

        # get initial quota defaults
        try:
            quota_defaults = quotas.get_default_quota_data(self.request)

            try:
                if api.base.is_service_enabled(self.request, 'network') and \
                        api.neutron.is_quotas_extension_supported(
                            self.request):
                    # TODO(jpichon): There is no API to access the Neutron
                    # default quotas (LP#1204956). For now, use the values
                    # from the current project.
                    project_id = self.request.user.project_id
                    quota_defaults += api.neutron.tenant_quota_get(
                        self.request,
                        tenant_id=project_id)
            except Exception:
                error_msg = _('Unable to retrieve default Neutron quota '
                              'values.')
                self.add_error_to_step(error_msg, 'create_quotas')

            for field in quotas.QUOTA_FIELDS:
                initial[field] = quota_defaults.get(field).limit

        except Exception:
            error_msg = _('Unable to retrieve default quota values.')
            self.add_error_to_step(error_msg, 'create_quotas')

        return initial

class UpdateProjectView(workflows.WorkflowView):
    is_billing_admin = False
    workflow_class = project_workflows.UpdateProject

    def get_initial(self):
        initial = super(UpdateProjectView, self).get_initial()

        project_id = self.kwargs['tenant_id']
        initial['project_id'] = project_id

        self.is_billing_admin = is_billing_admin(self.request)
        if self.is_billing_admin:
            self.ksclient = get_admin_ksclient()

        try:
            if self.is_billing_admin:
                project_info = self.ksclient.tenants.get(project_id)
            else:
                # get initial project info
                project_info = api.keystone.tenant_get(self.request, project_id,
                                                       admin=True)
            for field in PROJECT_INFO_FIELDS:
                initial[field] = getattr(project_info, field, None)

            # Retrieve the domain name where the project belong
            if keystone.VERSIONS.active >= 3:
                try:
                    if self.is_billing_admin:
                        domain = self.ksclient.domains.get(initial['domain_id'])
                    else:
                        domain = api.keystone.domain_get(self.request,
                                                         initial["domain_id"])
                    initial["domain_name"] = domain.name
                except Exception:
                    exceptions.handle(self.request,
                                      _('Unable to retrieve project domain.'),
                                      redirect=reverse(INDEX_URL))
            # request 'quota' data only if admin_or_owner (see nova policy.json)
            if policy.check((("compute", "os_compute_api:os-quota-sets:show"),), self.request, target={"project_id": project_id}):
                # get initial project quota
                quota_data = quotas.get_tenant_quota_data(self.request,
                                                          tenant_id=project_id)
                if api.base.is_service_enabled(self.request, 'network') and \
                        api.neutron.is_quotas_extension_supported(self.request):
                    quota_data += api.neutron.tenant_quota_get(
                        self.request, tenant_id=project_id)
                for field in quotas.QUOTA_FIELDS:
                    initial[field] = quota_data.get(field).limit
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))
        # handle address fields
        initial["address_street"] = getattr(project_info, "address_street", None)
        initial["address_city"] = getattr(project_info, "address_city", None)
        initial["address_state"] = getattr(project_info, "address_state", None)
        initial["address_zip"] =  getattr(project_info, "address_zip", None)
        initial["address_country"] = getattr(project_info, "address_country", 'US')
        initial["billing_balance"] = getattr(project_info, "billing_balance", None)
        initial["billing_cc_holder"] = getattr(project_info, "billing_cc_holder", None)
        initial["billing_cc_type"] = getattr(project_info, "billing_cc_type", '').upper()
        initial["billing_cc_number"] = getattr(project_info, "billing_cc_number", None)
        try:
            initial["billing_cc_number"] = decrypt(CIPHER_KEY, initial["billing_cc_number"])
        except:
            pass
        if initial["billing_cc_number"] != None:
            initial["billing_cc_number"] = '************' + initial["billing_cc_number"][-4:]
        initial["billing_cc_expire"] = getattr(project_info, "billing_cc_expire", None)
        # never store CC security code
        #if getattr(project_info, "billing_cc_sec_code", None) != None:
        #    initial["billing_cc_sec_code"] = "****"
        initial["billing_cc_sec_code"] = ''
        return initial


class DetailProjectView(generic.TemplateView):
    template_name = 'identity/xprojects/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailProjectView, self).get_context_data(**kwargs)
        project = self.get_data()
        table = project_tables.TenantsTable(self.request)
        context["project"] = project
        context["page_title"] = _("Project Details: %s") % project.name
        context["url"] = reverse(INDEX_URL)
        context["actions"] = table.render_row_actions(project)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            project_id = self.kwargs['project_id']
            if is_billing_admin(self.request):
                ks = get_admin_ksclient()
                project = ks.tenants.get(project_id)
            else:
                project = api.keystone.tenant_get(self.request, project_id)

        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))

        # adjust billing data
        if getattr(project, 'billing_cc_number', None) != None:
            project.billing_cc_number = '************' + decrypt(CIPHER_KEY, project.billing_cc_number)[-4:]

        return project


# adjust credit view
class AdjustCreditView(forms.ModalFormView):

    form_class = project_forms.AdjustCredit
    template_name = 'identity/xprojects/adjust_credit.html'
    modal_id = "adjust_credit_modal"
    modal_header = _("Adjust Credit")
    submit_label = _("Adjust Credit")
    submit_url = "horizon:identity:xprojects:adjust_credit"
    success_url = reverse_lazy('horizon:identity:xprojects:index')

    def get_initial(self):
        return {"project_id": self.kwargs["project_id"]}

    def get_context_data(self, **kwargs):
        context = super(AdjustCreditView, self).get_context_data(**kwargs)
        context['project_id'] = self.kwargs['project_id']
        context['submit_url'] = reverse(self.submit_url, args=[context['project_id']])
        return context
