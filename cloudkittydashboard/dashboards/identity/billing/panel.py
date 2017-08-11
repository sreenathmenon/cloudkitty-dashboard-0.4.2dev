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

from django.utils.translation import ugettext_lazy as _
from cloudkittydashboard.dashboards.identity.billing.ksclient import get_admin_ksclient

import horizon


class Billing(horizon.Panel):
    name = _("Billing")
    slug = "billing"

    def allowed(self, context):
        # check if user hasspecial role 'billing'
        user = context['request'].user.id
        tenant = context['request'].user.tenant_id
        keystone = get_admin_ksclient()
        roles = keystone.roles.roles_for_user(user, tenant)
        for role in roles:
            if role.id == 'billing' or role.name == 'billing':
                return True
        return False
