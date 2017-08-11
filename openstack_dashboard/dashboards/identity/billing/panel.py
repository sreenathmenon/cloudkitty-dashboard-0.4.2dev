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

from django.utils.translation import ugettext_lazy as _
import horizon

from openstack_dashboard.local.local_settings import BILLING_ROLE, OPENSTACK_API_VERSIONS
from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient

class Billing(horizon.Panel):
    name = _("Billing")
    slug = 'billing'
    #policy_rules = (("identity", "admin_required"),)

    def allowed(self, context):
        # check if user hasspecial role 'billing'
        user = context['request'].user.id
        tenant = context['request'].user.tenant_id
        keystone = get_admin_ksclient()
        if OPENSTACK_API_VERSIONS['identity'] == 3:
            roles = keystone.roles.list(user=user, project=tenant)
        else:
            roles = keystone.roles.roles_for_user(user, tenant)
        for role in roles:
            if role.id == BILLING_ROLE or role.name == BILLING_ROLE:
                return True
        return False

