from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient
from openstack_dashboard.local.local_settings import BILLING_ADMIN_ROLE, OPENSTACK_API_VERSIONS

# billing-admin policy check helper
def is_billing_admin(request):
    user = request.user.id
    tenant = request.user.tenant_id
    if not tenant:
        tenant = request.user.project_id
    keystone = get_admin_ksclient()
    if OPENSTACK_API_VERSIONS['identity'] == 3:
        roles = keystone.roles.list(user=user, project=tenant)
    else:
        roles = keystone.roles.roles_for_user(user, tenant)
    for role in roles:
        if role.name == BILLING_ADMIN_ROLE or role.id == BILLING_ADMIN_ROLE:
            return True
    return False
