from datetime import datetime

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import messages
from horizon import forms

from openstack_dashboard import api

from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient
from openstack_dashboard.dashboards.identity.xprojects.tools import is_billing_admin

from openstack_dashboard.local.local_settings import OPENSTACK_API_VERSIONS

class AdjustCredit(forms.SelfHandlingForm):

    project_id = forms.CharField(label=_("Project ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)

    amount = forms.FloatField(label=_("Amount"))
    reason = forms.CharField(label=_("Description"))

    def handle(self, request, data):
        try:
            if not is_billing_admin(request):
                return False

            project_id = data['project_id']

            if 'name' not in data:
                ks = get_admin_ksclient()
                if OPENSTACK_API_VERSIONS['identity'] == 3:
                    ks.tenants = ks.projects
                _data_ = ks.tenants.get(project_id)
                data['name'] = _data_.name
                data['description'] = _data_.description
                data['enabled'] = _data_.enabled

            ks = get_admin_ksclient()
            project_data = ks.tenants.get(project_id)
            extra = {}

            if hasattr(project_data, 'billing_credit'):
                extra['billing_credit'] = project_data.billing_credit
            else:
                extra['billing_credit'] = 0

            if hasattr(project_data, 'billing_credit_log'):
                extra['billing_credit_log'] = project_data.billing_credit_log
            else:
                extra['billing_credit_log'] = []

            extra['billing_credit'] = extra['billing_credit'] + data['amount']
            extra['billing_credit_log'].insert(0, {
                'date': datetime.now(),
                'user_id': request.user.id,
                'username': request.user.username,
                'amount': data['amount'],
                'reason': data['reason']
            })

            return ks.tenants.update(
                project_id,
                name=data['name'],
                description=data['description'],
                enabled=data['enabled'],
                **extra)

            messages.success('Project credit adjusted successfully.')
            return True
        except Exception:
            exceptions.handle(request, _('Unable to adjust project credit.'))
