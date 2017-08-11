from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon import views
from horizon.utils import memoized
from horizon.utils import functions as utils
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.api import keystone
from openstack_dashboard import policy
from openstack_dashboard import usage
from openstack_dashboard.usage import quotas

from urbaneclient import Client as UrbaneClient

from openstack_dashboard.dashboards.identity.signups import tables as signups_tables

from openstack_dashboard.local.local_settings import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_TENANT, ADMIN_DOMAIN, ADMIN_REGION, ADMIN_AUTH_URL, SIGNUP_CONTACT_EXTRA_LABEL

try:
    import simplejson as json
except ImportError:
    import json
except:
    raise

INDEX_URL = "horizon:identity:signups:index"


# signups table (index) view
class IndexView(tables.DataTableView):
    table_class = signups_tables.SignupsTable
    template_name = 'identity/signups/index.html'
    page_title = _("Signups")

    _has_more_data_ = False

    def has_more_data(self, table):
        return self._has_more_data_

    def has_prev_data(self, table):
        return table._page_ > 1

    def get_data(self):
        table = self.get_table()
        urbane = UrbaneClient(
            auth_url=ADMIN_AUTH_URL,
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
            # urbane client automatically discovers
            # Keystone API version from auth_url
            # and takes required parameter
            tenant=ADMIN_TENANT,
            domain=ADMIN_DOMAIN,
            region=ADMIN_REGION
        )
        table._page_ = int(self.request.GET.get(signups_tables.SignupsTable._meta.pagination_param, 1))
        if table._page_ < 1:
            table._page_ = 1
        page_size = utils.get_page_size(self.request)
        page_range = '%d:%d' % (table._page_, page_size)
        signups, total = urbane.list(range=page_range)
        # handle _has_more_data_
        self._has_more_data_ = (total // page_size) + 1 > table._page_
        return signups


# signup detail view
class DetailView(views.HorizonTemplateView):
    template_name = 'identity/signups/detail.html'
    page_title = _("Signup Details: {{ signup.id }}")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        urbane = UrbaneClient(
            auth_url=ADMIN_AUTH_URL,
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
            # urbane client automatically discovers
            # Keystone API version from auth_url
            # and takes required parameter
            tenant=ADMIN_TENANT,
            domain=ADMIN_DOMAIN,
            region=ADMIN_REGION
        )
        signup = urbane.get(id=kwargs['signup_id'])
        context['signup'] = signup.as_dict()
        context['signup']['extra_as_str'] = json.dumps(signup.extra, sort_keys=True, indent=4)

        context['contact_extra_label'] = SIGNUP_CONTACT_EXTRA_LABEL

        return context
