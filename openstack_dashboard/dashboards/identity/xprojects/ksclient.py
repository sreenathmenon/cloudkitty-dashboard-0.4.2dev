from openstack_dashboard.local.local_settings import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_TENANT, ADMIN_AUTH_URL, OPENSTACK_API_VERSIONS

if OPENSTACK_API_VERSIONS['identity'] == 3:
    from keystoneclient.v3 import client as ksclient
else:
    from keystoneclient.v2_0 import client as ksclient

def get_admin_ksclient():
    keystone = ksclient.Client(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        tenant_name=ADMIN_TENANT,
        auth_url=ADMIN_AUTH_URL
    )
    if OPENSTACK_API_VERSIONS['identity'] == 3:
        keystone.tenants = keystone.projects

    return keystone
