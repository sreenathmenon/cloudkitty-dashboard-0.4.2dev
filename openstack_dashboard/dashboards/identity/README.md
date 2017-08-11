`openstack_dashboard/local/local_settings.py` must contain following options:

```
# the 'billing' project id
BILLING_PROJECT = '<billing_project_id>'
# keystone admin auth credentials
ADMIN_USERNAME='admin'
ADMIN_PASSWORD='secret'
ADMIN_TENANT='admin'
ADMIN_AUTH_URL='http://localhost:5000/v2.0'
```

Only members of project `BILLING_PROJECT` will be able to edit 'Balance' field of specific tenant.

