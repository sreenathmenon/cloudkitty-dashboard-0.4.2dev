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
from django.utils.translation import ugettext_lazy as _
from django.views import generic

import six
import six.moves.urllib.parse as urlparse

from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import keystone
from openstack_dashboard import policy
from openstack_dashboard import usage
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.identity.billing \
    import tables as project_tables
from openstack_dashboard.dashboards.identity.billing \
    import workflows as project_workflows
from openstack_dashboard.dashboards.project.overview \
    import views as project_views

from openstack_dashboard.dashboards.identity.billing.cipher import decrypt
from openstack_dashboard.local.local_settings import CIPHER_KEY, OPENSTACK_API_VERSIONS

from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient

BILLING_INFO_FIELDS = (
    "id",
    "name",
    "enabled",
    "address_street",
    "address_city",
    "address_state",
    "address_zip",
    "address_country",
    "billing_balance",
    "billing_cc_holder",
    "billing_cc_type",
    "billing_cc_number",
    "billing_cc_expire",
    "billing_cc_sec_code"
)

INDEX_URL = "horizon:identity:billing:index"


class UpdateBillingView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateBilling

    def get_initial(self):
        initial = super(UpdateBillingView, self).get_initial()

        user_id = self.request.user.id
        project_id = self.request.user.project_id

        try:
            # connect to keystone as admin
            keystone = get_admin_ksclient()
            if OPENSTACK_API_VERSIONS['identity'] == 3:
                roles = keystone.roles.list(user=user_id, project=project_id)
            else:
                roles = keystone.roles.roles_for_user(user_id, project_id)
            project_info = keystone.tenants.get(project_id)

            for field in BILLING_INFO_FIELDS:
                initial[field] = getattr(project_info, field, None)

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
        initial["billing_cc_sec_code"]
        return initial


class IndexView(generic.TemplateView):
    template_name = 'identity/billing/detail.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        project = self.get_data()
        table = project_tables.ProjectsTable(self.request)
        context["project"] = project
        context["page_title"] = _("Project Details: %s") % project.name
        context["url"] = reverse(INDEX_URL)
        context["actions"] = table.render_row_actions(project)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            user_id =  self.request.user.id
            project_id = self.request.user.project_id

            # connect to keystone as 'billing' admin
            keystone = get_admin_ksclient()
            project = keystone.tenants.get(project_id)

        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))

        # adjust billing data
        if getattr(project, 'billing_cc_number', None) != None:
            project.billing_cc_number = '************' + decrypt(CIPHER_KEY, project.billing_cc_number)[-4:]

        return project
