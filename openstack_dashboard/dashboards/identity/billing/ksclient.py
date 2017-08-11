from keystoneclient.v2_0 import client as ksclient
from openstack_dashboard.local.local_settings import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_TENANT, ADMIN_AUTH_URL

def get_admin_ksclient():
    return ksclient.Client(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        tenant_name=ADMIN_TENANT,
        auth_url=ADMIN_AUTH_URL
    )
