from django.utils.translation import ugettext_lazy as _
import horizon

from openstack_dashboard.local.local_settings import SIGNUP_ROLES, OPENSTACK_API_VERSIONS
from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient

class Signups(horizon.Panel):
    name = _("Signups")
    slug = 'signups'

    def allowed(self, context):
        # check if user has special signup role
        user = context['request'].user.id
        tenant = context['request'].user.tenant_id
        keystone = get_admin_ksclient()
        if OPENSTACK_API_VERSIONS['identity'] == 3:
            roles = keystone.roles.list(user=user, project=tenant)
        else:
            roles = keystone.roles.roles_for_user(user, tenant)
        for role in roles:
            if role.name in SIGNUP_ROLES or role.id in SIGNUP_ROLES:
                return True
        return False
