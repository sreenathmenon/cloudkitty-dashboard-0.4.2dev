# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.exceptions import ValidationError  # noqa
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import exceptions
from horizon import forms
from horizon import tables
from keystoneclient.exceptions import Conflict  # noqa

from openstack_dashboard import api
from openstack_dashboard import policy


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

class UpdateBilling(tables.LinkAction):
    name = "update"
    verbose_name = _("Edit")
    url = "horizon:identity:billing:update"
    classes = ("ajax-modal",)
    icon = "pencil"
#    policy_rules = (('identity', 'identity:update_project'),)
    policy_rules = ('admin_or_owner',)

#    def allowed(self, request, project):
#        return api.keystone.keystone_can_edit_project()


class TenantFilterAction(tables.FilterAction):
    def filter(self, table, projects, filter_string):
        """Really naive case-insensitive search."""
        # FIXME(gabriel): This should be smarter. Written for demo purposes.
        q = filter_string.lower()

        def comp(tenant):
            if q in tenant.name.lower():
                return True
            return False

        return filter(comp, projects)


class BillingRow(tables.Row):
    ajax = True

    def get_data(self, request, project_id):
        project_info = api.keystone.tenant_get(request, project_id, admin=True)
        return {}
        return project_info

def render_address(billing):
    addr = [
        getattr(billing, 'address_street', None),
        getattr(billing, 'address_city', None),
        getattr(billing, 'address_state', None),
        getattr(billing, 'address_zip', None),
        getattr(billing, 'address_country', None)
    ]
    addr = [s for s in addr if s is not None]
    return ", ".join(addr)

class ProjectsTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Project Name'), link=("horizon:identity:billing:detail"))
    id = tables.Column('id', verbose_name=_('Project ID'))
    address = tables.Column(render_address, verbose_name=_('Address'))
    balance = tables.Column('billing_balance', verbose_name=_('Balance'))
    enabled = tables.Column('enabled', verbose_name=_('Enabled'), status=True, filters=(filters.yesno, filters.capfirst))

    class Meta(object):
        name = "projects"
        verbose_name = _("Billing")
        row_class = BillingRow
        row_actions = (UpdateBilling,)
        table_actions = (TenantFilterAction,)
        pagination_param = "tenant_marker"

