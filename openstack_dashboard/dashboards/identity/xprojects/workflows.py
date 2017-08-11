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

from cipher import encrypt, decrypt

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard.api import keystone
from openstack_dashboard.api import nova
from openstack_dashboard.usage import quotas

from openstack_dashboard import policy

from openstack_dashboard.local.local_settings import CIPHER_KEY, BILLING_ADMIN_ROLE, OPENSTACK_API_VERSIONS

from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient
from openstack_dashboard.dashboards.identity.xprojects.tools import is_billing_admin

INDEX_URL = "horizon:identity:xprojects:index"
ADD_USER_URL = "horizon:identity:xprojects:create_user"
PROJECT_GROUP_ENABLED = keystone.VERSIONS.active >= 3
PROJECT_USER_MEMBER_SLUG = "update_members"
PROJECT_GROUP_MEMBER_SLUG = "update_group_members"
COMMON_HORIZONTAL_TEMPLATE = "identity/xprojects/_common_horizontal_form.html"


# helper to extract extra fields from data
def get_extra(request, data):
    extra = {}
    # handle billing-admin fields
    if is_billing_admin(request):
        extra['address_street'] = data['address_street']
        extra['address_city'] = data['address_city']
        extra['address_state'] = data['address_state']
        extra['address_zip'] = data['address_zip']
        extra['address_country'] = data['address_country']
        extra['billing_balance'] = data['billing_balance']
        extra['billing_cc_holder'] = data['billing_cc_holder']
        extra['billing_cc_type'] = data['billing_cc_type']
        if len(data['billing_cc_number']) > 0 and data['billing_cc_number'][1] != '*':
            extra['billing_cc_number'] = encrypt(CIPHER_KEY, data['billing_cc_number'])
        extra['billing_cc_expire'] = data['billing_cc_expire']
    # never store CC security code
    #if data['billing_cc_sec_code'][1] != '*':
    #    extra['billing_cc_sec_code'] = cipher.encrypt(data['billing_cc_sec_code'])
    return extra

class ProjectQuotaAction(workflows.Action):
    ifcb_label = _("Injected File Content (Bytes)")
    metadata_items = forms.IntegerField(min_value=-1,
                                        label=_("Metadata Items"))
    cores = forms.IntegerField(min_value=-1, label=_("VCPUs"))
    instances = forms.IntegerField(min_value=-1, label=_("Instances"))
    injected_files = forms.IntegerField(min_value=-1,
                                        label=_("Injected Files"))
    injected_file_content_bytes = forms.IntegerField(min_value=-1,
                                                     label=ifcb_label)
    volumes = forms.IntegerField(min_value=-1, label=_("Volumes"))
    snapshots = forms.IntegerField(min_value=-1, label=_("Volume Snapshots"))
    gigabytes = forms.IntegerField(
        min_value=-1, label=_("Total Size of Volumes and Snapshots (GB)"))
    ram = forms.IntegerField(min_value=-1, label=_("RAM (MB)"))
    floating_ips = forms.IntegerField(min_value=-1, label=_("Floating IPs"))
    fixed_ips = forms.IntegerField(min_value=-1, label=_("Fixed IPs"))
    security_groups = forms.IntegerField(min_value=-1,
                                         label=_("Security Groups"))
    security_group_rules = forms.IntegerField(min_value=-1,
                                              label=_("Security Group Rules"))

    # Neutron
    security_group = forms.IntegerField(min_value=-1,
                                        label=_("Security Groups"))
    security_group_rule = forms.IntegerField(min_value=-1,
                                             label=_("Security Group Rules"))
    floatingip = forms.IntegerField(min_value=-1, label=_("Floating IPs"))
    network = forms.IntegerField(min_value=-1, label=_("Networks"))
    port = forms.IntegerField(min_value=-1, label=_("Ports"))
    router = forms.IntegerField(min_value=-1, label=_("Routers"))
    subnet = forms.IntegerField(min_value=-1, label=_("Subnets"))

    def __init__(self, request, *args, **kwargs):
        super(ProjectQuotaAction, self).__init__(request,
                                                 *args,
                                                 **kwargs)
        disabled_quotas = quotas.get_disabled_quotas(request)
        for field in disabled_quotas:
            if field in self.fields:
                self.fields[field].required = False
                self.fields[field].widget = forms.HiddenInput()


class UpdateProjectQuotaAction(ProjectQuotaAction):
    def clean(self):
        cleaned_data = super(UpdateProjectQuotaAction, self).clean()
        usages = quotas.tenant_quota_usages(
            self.request, tenant_id=self.initial['project_id'])
        # Validate the quota values before updating quotas.
        bad_values = []
        for key, value in cleaned_data.items():
            used = usages[key].get('used', 0)
            if value is not None and value >= 0 and used > value:
                bad_values.append(_('%(used)s %(key)s used') %
                                  {'used': used,
                                   'key': quotas.QUOTA_NAMES.get(key, key)})
        if bad_values:
            value_str = ", ".join(bad_values)
            msg = (_('Quota value(s) cannot be less than the current usage '
                     'value(s): %s.') %
                   value_str)
            raise forms.ValidationError(msg)
        return cleaned_data

    class Meta(object):
        name = _("Quota")
        slug = 'update_quotas'
        help_text = _("Set maximum quotas for the project.")


class CreateProjectQuotaAction(ProjectQuotaAction):
    class Meta(object):
        name = _("Quota")
        slug = 'create_quotas'
        help_text = _("Set maximum quotas for the project.")


class UpdateProjectQuota(workflows.Step):
    action_class = UpdateProjectQuotaAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    depends_on = ("project_id",)
    contributes = quotas.QUOTA_FIELDS


class CreateProjectQuota(workflows.Step):
    action_class = CreateProjectQuotaAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    depends_on = ("project_id",)
    contributes = quotas.QUOTA_FIELDS


class CreateProjectInfoAction(workflows.Action):
    # Hide the domain_id and domain_name by default
    domain_id = forms.CharField(label=_("Domain ID"),
                                required=False,
                                widget=forms.HiddenInput())
    domain_name = forms.CharField(label=_("Domain Name"),
                                  required=False,
                                  widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"),
                           max_length=64)
    description = forms.CharField(widget=forms.widgets.Textarea(
                                  attrs={'rows': 4}),
                                  label=_("Description"),
                                  required=False)
    enabled = forms.BooleanField(label=_("Enabled"),
                                 required=False,
                                 initial=True)

    def __init__(self, request, *args, **kwargs):
        super(CreateProjectInfoAction, self).__init__(request,
                                                      *args,
                                                      **kwargs)
        # For keystone V3, display the two fields in read-only
        if keystone.VERSIONS.active >= 3:
            readonlyInput = forms.TextInput(attrs={'readonly': 'readonly'})
            self.fields["domain_id"].widget = readonlyInput
            self.fields["domain_name"].widget = readonlyInput

    class Meta(object):
        name = _("Project Information")
        help_text = _("Create a project to organize users.")


class CreateProjectInfo(workflows.Step):
    action_class = CreateProjectInfoAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    contributes = ("domain_id",
                   "domain_name",
                   "project_id",
                   "name",
                   "description",
                   "enabled")

countries = (
    ('AD', 'Andorra'),
    ('AE', 'United Arab Emirates'),
    ('AF', 'Afghanistan'),
    ('AG', 'Antigua & Barbuda'),
    ('AI', 'Anguilla'),
    ('AL', 'Albania'),
    ('AM', 'Armenia'),
    ('AN', 'Netherlands Antilles'),
    ('AO', 'Angola'),
    ('AQ', 'Antarctica'),
    ('AR', 'Argentina'),
    ('AS', 'American Samoa'),
    ('AT', 'Austria'),
    ('AU', 'Australia'),
    ('AW', 'Aruba'),
    ('AZ', 'Azerbaijan'),
    ('BA', 'Bosnia and Herzegovina'),
    ('BB', 'Barbados'),
    ('BD', 'Bangladesh'),
    ('BE', 'Belgium'),
    ('BF', 'Burkina Faso'),
    ('BG', 'Bulgaria'),
    ('BH', 'Bahrain'),
    ('BI', 'Burundi'),
    ('BJ', 'Benin'),
    ('BM', 'Bermuda'),
    ('BN', 'Brunei Darussalam'),
    ('BO', 'Bolivia'),
    ('BR', 'Brazil'),
    ('BS', 'Bahama'),
    ('BT', 'Bhutan'),
    ('BU', 'Burma (no longer exists)'),
    ('BV', 'Bouvet Island'),
    ('BW', 'Botswana'),
    ('BY', 'Belarus'),
    ('BZ', 'Belize'),
    ('CA', 'Canada'),
    ('CC', 'Cocos (Keeling) Islands'),
    ('CF', 'Central African Republic'),
    ('CG', 'Congo'),
    ('CH', 'Switzerland'),
    ('CI', 'Cote d\'Ivoire (Ivory Coast)'),
    ('CK', 'Cook Iislands'),
    ('CL', 'Chile'),
    ('CM', 'Cameroon'),
    ('CN', 'China'),
    ('CO', 'Colombia'),
    ('CR', 'Costa Rica'),
    ('CS', 'Czechoslovakia (no longer exists)'),
    ('CU', 'Cuba'),
    ('CV', 'Cape Verde'),
    ('CX', 'Christmas Island'),
    ('CY', 'Cyprus'),
    ('CZ', 'Czech Republic'),
    ('DD', 'German Democratic Republic (no longer exists)'),
    ('DE', 'Germany'),
    ('DJ', 'Djibouti'),
    ('DK', 'Denmark'),
    ('DM', 'Dominica'),
    ('DO', 'Dominican Republic'),
    ('DZ', 'Algeria'),
    ('EC', 'Ecuador'),
    ('EE', 'Estonia'),
    ('EG', 'Egypt'),
    ('EH', 'Western Sahara'),
    ('ER', 'Eritrea'),
    ('ES', 'Spain'),
    ('ET', 'Ethiopia'),
    ('FI', 'Finland'),
    ('FJ', 'Fiji'),
    ('FK', 'Falkland Islands (Malvinas)'),
    ('FM', 'Micronesia'),
    ('FO', 'Faroe Islands'),
    ('FR', 'France'),
    ('FX', 'France, Metropolitan'),
    ('GA', 'Gabon'),
    ('GB', 'United Kingdom (Great Britain)'),
    ('GD', 'Grenada'),
    ('GE', 'Georgia'),
    ('GF', 'French Guiana'),
    ('GH', 'Ghana'),
    ('GI', 'Gibraltar'),
    ('GL', 'Greenland'),
    ('GM', 'Gambia'),
    ('GN', 'Guinea'),
    ('GP', 'Guadeloupe'),
    ('GQ', 'Equatorial Guinea'),
    ('GR', 'Greece'),
    ('GS', 'South Georgia and the South Sandwich Islands'),
    ('GT', 'Guatemala'),
    ('GU', 'Guam'),
    ('GW', 'Guinea-Bissau'),
    ('GY', 'Guyana'),
    ('HK', 'Hong Kong'),
    ('HM', 'Heard & McDonald Islands'),
    ('HN', 'Honduras'),
    ('HR', 'Croatia'),
    ('HT', 'Haiti'),
    ('HU', 'Hungary'),
    ('ID', 'Indonesia'),
    ('IE', 'Ireland'),
    ('IL', 'Israel'),
    ('IN', 'India'),
    ('IO', 'British Indian Ocean Territory'),
    ('IQ', 'Iraq'),
    ('IR', 'Islamic Republic of Iran'),
    ('IS', 'Iceland'),
    ('IT', 'Italy'),
    ('JM', 'Jamaica'),
    ('JO', 'Jordan'),
    ('JP', 'Japan'),
    ('KE', 'Kenya'),
    ('KG', 'Kyrgyzstan'),
    ('KH', 'Cambodia'),
    ('KI', 'Kiribati'),
    ('KM', 'Comoros'),
    ('KN', 'St. Kitts and Nevis'),
    ('KP', 'Korea, Democratic People\'s Republic of'),
    ('KR', 'Korea, Republic of'),
    ('KW', 'Kuwait'),
    ('KY', 'Cayman Islands'),
    ('KZ', 'Kazakhstan'),
    ('LA', 'Lao People\'s Democratic Republic'),
    ('LB', 'Lebanon'),
    ('LC', 'Saint Lucia'),
    ('LI', 'Liechtenstein'),
    ('LK', 'Sri Lanka'),
    ('LR', 'Liberia'),
    ('LS', 'Lesotho'),
    ('LT', 'Lithuania'),
    ('LU', 'Luxembourg'),
    ('LV', 'Latvia'),
    ('LY', 'Libyan Arab Jamahiriya'),
    ('MA', 'Morocco'),
    ('MC', 'Monaco'),
    ('MD', 'Moldova, Republic of'),
    ('MG', 'Madagascar'),
    ('MH', 'Marshall Islands'),
    ('ML', 'Mali'),
    ('MN', 'Mongolia'),
    ('MM', 'Myanmar'),
    ('MO', 'Macau'),
    ('MP', 'Northern Mariana Islands'),
    ('MQ', 'Martinique'),
    ('MR', 'Mauritania'),
    ('MS', 'Monserrat'),
    ('MT', 'Malta'),
    ('MU', 'Mauritius'),
    ('MV', 'Maldives'),
    ('MW', 'Malawi'),
    ('MX', 'Mexico'),
    ('MY', 'Malaysia'),
    ('MZ', 'Mozambique'),
    ('NA', 'Namibia'),
    ('NC', 'New Caledonia'),
    ('NE', 'Niger'),
    ('NF', 'Norfolk Island'),
    ('NG', 'Nigeria'),
    ('NI', 'Nicaragua'),
    ('NL', 'Netherlands'),
    ('NO', 'Norway'),
    ('NP', 'Nepal'),
    ('NR', 'Nauru'),
    ('NT', 'Neutral Zone (no longer exists)'),
    ('NU', 'Niue'),
    ('NZ', 'New Zealand'),
    ('OM', 'Oman'),
    ('PA', 'Panama'),
    ('PE', 'Peru'),
    ('PF', 'French Polynesia'),
    ('PG', 'Papua New Guinea'),
    ('PH', 'Philippines'),
    ('PK', 'Pakistan'),
    ('PL', 'Poland'),
    ('PM', 'St. Pierre & Miquelon'),
    ('PN', 'Pitcairn'),
    ('PR', 'Puerto Rico'),
    ('PT', 'Portugal'),
    ('PW', 'Palau'),
    ('PY', 'Paraguay'),
    ('QA', 'Qatar'),
    ('RE', 'Reunion'),
    ('RO', 'Romania'),
    ('RU', 'Russian Federation'),
    ('RW', 'Rwanda'),
    ('SA', 'Saudi Arabia'),
    ('SB', 'Solomon Islands'),
    ('SC', 'Seychelles'),
    ('SD', 'Sudan'),
    ('SE', 'Sweden'),
    ('SG', 'Singapore'),
    ('SH', 'St. Helena'),
    ('SI', 'Slovenia'),
    ('SJ', 'Svalbard & Jan Mayen Islands'),
    ('SK', 'Slovakia'),
    ('SL', 'Sierra Leone'),
    ('SM', 'San Marino'),
    ('SN', 'Senegal'),
    ('SO', 'Somalia'),
    ('SR', 'Suriname'),
    ('ST', 'Sao Tome & Principe'),
    ('SU', 'Union of Soviet Socialist Republics (no longer exists)'),
    ('SV', 'El Salvador'),
    ('SY', 'Syrian Arab Republic'),
    ('SZ', 'Swaziland'),
    ('TC', 'Turks & Caicos Islands'),
    ('TD', 'Chad'),
    ('TF', 'French Southern Territories'),
    ('TG', 'Togo'),
    ('TH', 'Thailand'),
    ('TJ', 'Tajikistan'),
    ('TK', 'Tokelau'),
    ('TM', 'Turkmenistan'),
    ('TN', 'Tunisia'),
    ('TO', 'Tonga'),
    ('TP', 'East Timor'),
    ('TR', 'Turkey'),
    ('TT', 'Trinidad & Tobago'),
    ('TV', 'Tuvalu'),
    ('TW', 'Taiwan, Province of China'),
    ('TZ', 'Tanzania, United Republic of'),
    ('UA', 'Ukraine'),
    ('UG', 'Uganda'),
    ('UM', 'United States Minor Outlying Islands'),
    ('US', 'United States of America'),
    ('UY', 'Uruguay'),
    ('UZ', 'Uzbekistan'),
    ('VA', 'Vatican City State (Holy See)'),
    ('VC', 'St. Vincent & the Grenadines'),
    ('VE', 'Venezuela'),
    ('VG', 'British Virgin Islands'),
    ('VI', 'United States Virgin Islands'),
    ('VN', 'Viet Nam'),
    ('VU', 'Vanuatu'),
    ('WF', 'Wallis & Futuna Islands'),
    ('WS', 'Samoa'),
    ('YD', 'Democratic Yemen (no longer exists)'),
    ('YE', 'Yemen'),
    ('YT', 'Mayotte'),
    ('YU', 'Yugoslavia'),
    ('ZA', 'South Africa'),
    ('ZM', 'Zambia'),
    ('ZR', 'Zaire'),
    ('ZW', 'Zimbabwe'),
    ('ZZ', 'Unknown or unspecified country')
)

class ProjectAddressAction(workflows.Action):
    address_street = forms.CharField(label=_("Street"), required=False)
    address_city = forms.CharField(label=_("City"), required=False)
    address_state = forms.CharField(label=_("State / Region"), required=False)
    address_zip = forms.CharField(label=_("ZIP Code"), required=False)
    address_country = forms.ChoiceField(label=_("Country"), choices=countries, initial='US', required=False)

    def __init__(self, request, *args, **kwargs):
        super(ProjectAddressAction, self).__init__(request,
                                                 *args,
                                                 **kwargs)
    class Meta(object):
        name = _("Address")


class ProjectAddress(workflows.Step):
    action_class = ProjectAddressAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    contributes = (
        "address_street",
        "address_city",
        "address_state",
        "address_zip",
        "address_country"
    )

cc_types = (
    ('AX', 'American Express'),
    ('MC', 'Mastercard'),
    ('VS', 'Visa')
)

cc_number_regexp="^(?:\*.*|4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})$"

months = (
    ('01', 'January'),
    ('02', 'February'),
    ('03', 'March'),
    ('04', 'April'),
    ('05', 'May'),
    ('06', 'June'),
    ('07', 'July'),
    ('08', 'August'),
    ('09', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
)

from datetime import date

years = []

for year in range(date.today().year, date.today().year + 15, 1):
    years.append([year, year])

class CCExpireWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        year = date.today().year
        widgets = [
            forms.SelectWidget(choices=months, attrs={"style":"display:inline;width:50%"}),
            forms.SelectWidget(choices=years, attrs={"style":"display:inline;width:50%"})
        ]
        super(CCExpireWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split("/")
        else:
            return [None, None]

class CCExpireField(forms.MultiValueField):
    widget = CCExpireWidget

    def __init__(self, *args, **kwargs):
        year = date.today().year
        fields = [
            forms.ChoiceField(choices=months),
            forms.ChoiceField(choices=years)
        ]
        super(CCExpireField, self).__init__(fields, *args, **kwargs)

    def compress(self, values):
        if len(values) < 2:
            return '/'
        else:
            return values[0] + '/' + values[1]


class ProjectBillingAction(workflows.Action):
    billing_balance = forms.FloatField(label=_("Balance"), required=False)
    billing_cc_holder = forms.CharField(label=_("Credit Card Holder"), required=False)
    billing_cc_type = forms.ChoiceField(label=_("Credit Card Type"), choices=cc_types, required=False)
    billing_cc_number = forms.RegexField(cc_number_regexp, label=_("Credit Card Number"), min_length=13, max_length=16, required=False)
    billing_cc_expire = CCExpireField(label=_("Credit Card Expire"), required=False)
    billing_cc_sec_code = forms.RegexField("^(?:\*.*|\d{3,4})$", label=_("CC Security Code"), min_length=3, max_length=4, required=False)

    def __init__(self, request, *args, **kwargs):
        super(ProjectBillingAction, self).__init__(request,
                                                 *args,
                                                 **kwargs)

        if not is_billing_admin(self.request):
           readonlyInput = forms.TextInput(attrs={'readonly': 'readonly'})
           self.fields["billing_balance"].widget = readonlyInput

        if 'project_id' in self.initial:
            self.fields['project_id'] = forms.Field(widget=forms.HiddenInput(), initial=self.initial['project_id'], required=False)

    class Meta(object):
        name = _("Billing")
        slug = "update_billing"


class ProjectBilling(workflows.Step):
    action_class = ProjectBillingAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    depends_on = ("project_id",)
    contributes = (
        "billing_balance",
        "billing_cc_holder",
        "billing_cc_type",
        "billing_cc_number",
        "billing_cc_expire",
        "billing_cc_sec_code"
    )


class UpdateProjectMembersAction(workflows.MembershipAction):
    def __init__(self, request, *args, **kwargs):
        super(UpdateProjectMembersAction, self).__init__(request,
                                                         *args,
                                                         **kwargs)
        err_msg = _('Unable to retrieve user list. Please try again later.')
        # Use the domain_id from the project
        domain_id = self.initial.get("domain_id", None)
        project_id = ''
        if 'project_id' in self.initial:
            project_id = self.initial['project_id']

        # Get the default role
        try:
            default_role = api.keystone.get_default_role(self.request)
            # Default role is necessary to add members to a project
            if default_role is None:
                default = getattr(settings,
                                  "OPENSTACK_KEYSTONE_DEFAULT_ROLE", None)
                msg = (_('Could not find default role "%s" in Keystone') %
                       default)
                raise exceptions.NotFound(msg)
        except Exception:
            exceptions.handle(self.request,
                              err_msg,
                              redirect=reverse(INDEX_URL))
        default_role_name = self.get_default_role_field_name()
        self.fields[default_role_name] = forms.CharField(required=False)
        self.fields[default_role_name].initial = default_role.id

        # Get list of available users
        all_users = []
        try:
            all_users = api.keystone.user_list(request,
                                               domain=domain_id)
        except Exception:
            exceptions.handle(request, err_msg)
        users_list = [(user.id, user.name) for user in all_users]

        # Get list of roles
        role_list = []
        try:
            role_list = api.keystone.role_list(request)
        except Exception:
            exceptions.handle(request,
                              err_msg,
                              redirect=reverse(INDEX_URL))
        for role in role_list:
            field_name = self.get_member_field_name(role.id)
            label = role.name
            self.fields[field_name] = forms.MultipleChoiceField(required=False,
                                                                label=label)
            self.fields[field_name].choices = users_list
            self.fields[field_name].initial = []

        # Figure out users & roles
        if project_id:
            try:
                users_roles = api.keystone.get_project_users_roles(request,
                                                                   project_id)
            except Exception:
                exceptions.handle(request,
                                  err_msg,
                                  redirect=reverse(INDEX_URL))

            for user_id in users_roles:
                roles_ids = users_roles[user_id]
                for role_id in roles_ids:
                    field_name = self.get_member_field_name(role_id)
                    self.fields[field_name].initial.append(user_id)

    class Meta(object):
        name = _("Project Members")
        slug = PROJECT_USER_MEMBER_SLUG


class UpdateProjectMembers(workflows.UpdateMembersStep):
    action_class = UpdateProjectMembersAction
    available_list_title = _("All Users")
    members_list_title = _("Project Members")
    no_available_text = _("No users found.")
    no_members_text = _("No users.")

    def contribute(self, data, context):
        if data:
            try:
                roles = api.keystone.role_list(self.workflow.request)
            except Exception:
                exceptions.handle(self.workflow.request,
                                  _('Unable to retrieve user list.'))

            post = self.workflow.request.POST
            for role in roles:
                field = self.get_member_field_name(role.id)
                context[field] = post.getlist(field)
        return context


class UpdateProjectGroupsAction(workflows.MembershipAction):
    def __init__(self, request, *args, **kwargs):
        super(UpdateProjectGroupsAction, self).__init__(request,
                                                        *args,
                                                        **kwargs)
        err_msg = _('Unable to retrieve group list. Please try again later.')
        # Use the domain_id from the project
        domain_id = self.initial.get("domain_id", None)
        project_id = ''
        if 'project_id' in self.initial:
            project_id = self.initial['project_id']

        # Get the default role
        try:
            default_role = api.keystone.get_default_role(self.request)
            # Default role is necessary to add members to a project
            if default_role is None:
                default = getattr(settings,
                                  "OPENSTACK_KEYSTONE_DEFAULT_ROLE", None)
                msg = (_('Could not find default role "%s" in Keystone') %
                       default)
                raise exceptions.NotFound(msg)
        except Exception:
            exceptions.handle(self.request,
                              err_msg,
                              redirect=reverse(INDEX_URL))
        default_role_name = self.get_default_role_field_name()
        self.fields[default_role_name] = forms.CharField(required=False)
        self.fields[default_role_name].initial = default_role.id

        # Get list of available groups
        all_groups = []
        try:
            if is_billing_admin(request):
                ks = get_admin_ksclient(request)
                #if OPENSTACK_API_VERSIONS['identity'] == 3:
                all_groups = ks.groups.list(domain=domain_id)
            else:
                all_groups = api.keystone.group_list(request,
                                                     domain=domain_id)
        except Exception:
            exceptions.handle(request, err_msg)
        groups_list = [(group.id, group.name) for group in all_groups]

        # Get list of roles
        role_list = []
        try:
            role_list = api.keystone.role_list(request)
        except Exception:
            exceptions.handle(request,
                              err_msg,
                              redirect=reverse(INDEX_URL))
        for role in role_list:
            field_name = self.get_member_field_name(role.id)
            label = role.name
            self.fields[field_name] = forms.MultipleChoiceField(required=False,
                                                                label=label)
            self.fields[field_name].choices = groups_list
            self.fields[field_name].initial = []

        # Figure out groups & roles
        if project_id:
            try:
                groups_roles = api.keystone.get_project_groups_roles(
                    request, project_id)
            except Exception:
                exceptions.handle(request,
                                  err_msg,
                                  redirect=reverse(INDEX_URL))

            for group_id in groups_roles:
                roles_ids = groups_roles[group_id]
                for role_id in roles_ids:
                    field_name = self.get_member_field_name(role_id)
                    self.fields[field_name].initial.append(group_id)

    class Meta(object):
        name = _("Project Groups")
        slug = PROJECT_GROUP_MEMBER_SLUG


class UpdateProjectGroups(workflows.UpdateMembersStep):
    action_class = UpdateProjectGroupsAction
    available_list_title = _("All Groups")
    members_list_title = _("Project Groups")
    no_available_text = _("No groups found.")
    no_members_text = _("No groups.")

    def contribute(self, data, context):
        if data:
            try:
                roles = api.keystone.role_list(self.workflow.request)
            except Exception:
                exceptions.handle(self.workflow.request,
                                  _('Unable to retrieve role list.'))

            post = self.workflow.request.POST
            for role in roles:
                field = self.get_member_field_name(role.id)
                context[field] = post.getlist(field)
        return context


class CommonQuotaWorkflow(workflows.Workflow):
    def _update_project_quota(self, request, data, project_id):
        # Update the project quota.
        nova_data = dict(
            [(key, data[key]) for key in quotas.NOVA_QUOTA_FIELDS])
        nova.tenant_quota_update(request, project_id, **nova_data)

        if base.is_service_enabled(request, 'volume'):
            cinder_data = dict([(key, data[key]) for key in
                                quotas.CINDER_QUOTA_FIELDS])
            cinder.tenant_quota_update(request,
                                       project_id,
                                       **cinder_data)

        if api.base.is_service_enabled(request, 'network') and \
                api.neutron.is_quotas_extension_supported(request):
            neutron_data = {}
            disabled_quotas = quotas.get_disabled_quotas(request)
            for key in quotas.NEUTRON_QUOTA_FIELDS:
                if key not in disabled_quotas:
                    neutron_data[key] = data[key]
            api.neutron.tenant_quota_update(request,
                                            project_id,
                                            **neutron_data)


class CreateProject(CommonQuotaWorkflow):
    slug = "create_project"
    name = _("Create Project")
    finalize_button_name = _("Create Project")
    success_message = _('Created new project "%s".')
    failure_message = _('Unable to create project "%s".')
    success_url = "horizon:identity:xprojects:index"
    default_steps = (CreateProjectInfo,
                     UpdateProjectMembers,
                     CreateProjectQuota,)

    def __init__(self, request=None, context_seed=None, entry_point=None,
                 *args, **kwargs):
        # unregister ProjectBilling & ProjectAddress from workflow
        try:
            self.unregister(ProjectBilling)
        except:
            pass
        try:
            self.unregister(ProjectAddress)
        except:
            pass

        if PROJECT_GROUP_ENABLED:
            self.default_steps = (CreateProjectInfo,
                                  UpdateProjectMembers,
                                  UpdateProjectGroups,
                                  CreateProjectQuota,)

        if is_billing_admin(request):
            self.default_steps = self.default_steps + (ProjectBilling, ProjectAddress,)

        super(CreateProject, self).__init__(request=request,
                                            context_seed=context_seed,
                                            entry_point=entry_point,
                                            *args,
                                            **kwargs)

    def format_status_message(self, message):
        if "%s" in message:
            return message % self.context.get('name', 'unknown project')
        else:
            return message

    def _create_project(self, request, data):
        # create the project
        domain_id = data['domain_id']
        try:
            desc = data['description']
            extra = get_extra(request, data)
            self.object = api.keystone.tenant_create(request,
                                                     name=data['name'],
                                                     description=desc,
                                                     enabled=data['enabled'],
                                                     domain=domain_id,
                                                     **extra)
            return self.object
        except exceptions.Conflict:
            msg = _('Project name "%s" is already used.') % data['name']
            self.failure_message = msg
            return
        except Exception:
            exceptions.handle(request, ignore=True)
            return

    def _update_project_members(self, request, data, project_id):
        # update project members
        users_to_add = 0
        try:
            available_roles = api.keystone.role_list(request)
            member_step = self.get_step(PROJECT_USER_MEMBER_SLUG)
            # count how many users are to be added
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                role_list = data[field_name]
                users_to_add += len(role_list)
            # add new users to project
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                role_list = data[field_name]
                users_added = 0
                for user in role_list:
                    api.keystone.add_tenant_user_role(request,
                                                      project=project_id,
                                                      user=user,
                                                      role=role.id)
                    users_added += 1
                users_to_add -= users_added
        except Exception:
            if PROJECT_GROUP_ENABLED:
                group_msg = _(", add project groups")
            else:
                group_msg = ""
            exceptions.handle(request,
                              _('Failed to add %(users_to_add)s project '
                                'members%(group_msg)s and set project quotas.')
                              % {'users_to_add': users_to_add,
                                 'group_msg': group_msg})

    def _update_project_groups(self, request, data, project_id):
        # update project groups
        groups_to_add = 0
        try:
            available_roles = api.keystone.role_list(request)
            member_step = self.get_step(PROJECT_GROUP_MEMBER_SLUG)

            # count how many groups are to be added
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                role_list = data[field_name]
                groups_to_add += len(role_list)
            # add new groups to project
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                role_list = data[field_name]
                groups_added = 0
                for group in role_list:
                    api.keystone.add_group_role(request,
                                                role=role.id,
                                                group=group,
                                                project=project_id)
                    groups_added += 1
                groups_to_add -= groups_added
        except Exception:
            exceptions.handle(request,
                              _('Failed to add %s project groups '
                                'and update project quotas.')
                              % groups_to_add)

    def _update_project_quota(self, request, data, project_id):
        try:
            super(CreateProject, self)._update_project_quota(
                request, data, project_id)
        except Exception:
            exceptions.handle(request, _('Unable to set project quotas.'))

    def handle(self, request, data):
        project = self._create_project(request, data)
        if not project:
            return False
        project_id = project.id
        self._update_project_members(request, data, project_id)
        if PROJECT_GROUP_ENABLED:
            self._update_project_groups(request, data, project_id)
        self._update_project_quota(request, data, project_id)
        return True


class UpdateProjectInfoAction(CreateProjectInfoAction):
    enabled = forms.BooleanField(required=False, label=_("Enabled"))

    def __init__(self, request, initial, *args, **kwargs):
        super(UpdateProjectInfoAction, self).__init__(
            request, initial, *args, **kwargs)
        if initial['project_id'] == request.user.project_id:
            self.fields['enabled'].widget.attrs['disabled'] = True
            self.fields['enabled'].help_text = _(
                'You cannot disable your current project')

    def clean(self):
        cleaned_data = super(UpdateProjectInfoAction, self).clean()
        # NOTE(tsufiev): in case the current project is being edited, its
        # 'enabled' field is disabled to prevent changing the field value
        # which is always `True` for the current project (because the user
        # logged in it). Since Django treats disabled checkbox as providing
        # `False` value even if its initial value is `True`, we need to
        # restore the original `True` value of 'enabled' field here.
        if self.fields['enabled'].widget.attrs.get('disabled', False):
            cleaned_data['enabled'] = True
        return cleaned_data

    class Meta(object):
        name = _("Project Information")
        slug = 'update_info'
        help_text = _("Edit the project details.")


class UpdateProjectInfo(workflows.Step):
    action_class = UpdateProjectInfoAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    depends_on = ("project_id",)
    contributes = ("domain_id",
                   "domain_name",
                   "name",
                   "description",
                   "enabled")


class UpdateProject(CommonQuotaWorkflow):
    slug = "update_project"
    name = _("Edit Project")
    finalize_button_name = _("Save")
    success_message = _('Modified project "%s".')
    failure_message = _('Unable to modify project "%s".')
    success_url = "horizon:identity:xprojects:index"
    default_steps = (UpdateProjectInfo,
                     UpdateProjectMembers,
                     UpdateProjectQuota)

    def __init__(self, request=None, context_seed=None, entry_point=None,
                 *args, **kwargs):
        # unregister ProjectBilling & ProjectAddress from workflow
        try:
            self.unregister(ProjectBilling)
        except:
            pass
        try:
            self.unregister(ProjectAddress)
        except:
            pass

        if PROJECT_GROUP_ENABLED:
            self.default_steps = (UpdateProjectInfo,
                                  UpdateProjectMembers,
                                  UpdateProjectGroups,
                                  UpdateProjectQuota)

        if is_billing_admin(request):
            if policy.check((("identity", "rule:is_admin"),), request):
                self.default_steps = self.default_steps + (ProjectBilling, ProjectAddress)
            else:
                self.default_steps = (ProjectBilling, ProjectAddress)

        super(UpdateProject, self).__init__(request=request,
                                            context_seed=context_seed,
                                            entry_point=entry_point,
                                            *args,
                                            **kwargs)

    def format_status_message(self, message):
        if "%s" in message:
            return message % self.context.get('name', 'unknown project')
        else:
            return message

    @memoized.memoized_method
    def _get_available_roles(self, request):
        return api.keystone.role_list(request)

    def _update_project(self, request, data):
        # update project info
        try:
            project_id = data['project_id']
            try:
                extra = get_extra(request, data)
            except:
                extra = {}

            if 'name' not in data:
                ks = get_admin_ksclient()
                if OPENSTACK_API_VERSIONS['identity'] == 3:
                    ks.tenants = ks.projects
                _data_ = ks.tenants.get(project_id)
                data['name'] = _data_.name
                data['description'] = _data_.description
                data['enabled'] = _data_.enabled

            if is_billing_admin(request):
                ks = get_admin_ksclient()
                return ks.tenants.update(
                    project_id,
                    name=data['name'],
                    description=data['description'],
                    enabled=data['enabled'],
                    **extra)
            else:
                return api.keystone.tenant_update(
                    request,
                    project_id,
                    name=data['name'],
                    description=data['description'],
                    enabled=data['enabled'],
                    **extra)
        except exceptions.Conflict:
            msg = _('Project name "%s" is already used.') % data['name']
            self.failure_message = msg
            return
        except Exception:
            exceptions.handle(request, ignore=True)
            return

    def _add_roles_to_users(self, request, data, project_id, user_id,
                            role_ids, available_roles):
        member_step = self.get_step(PROJECT_USER_MEMBER_SLUG)
        current_role_ids = list(role_ids)

        for role in available_roles:
            field_name = member_step.get_member_field_name(role.id)
            # Check if the user is in the list of users with this role.
            if user_id in data[field_name]:
                # Add it if necessary
                if role.id not in current_role_ids:
                    # user role has changed
                    api.keystone.add_tenant_user_role(
                        request,
                        project=project_id,
                        user=user_id,
                        role=role.id)
                else:
                    # User role is unchanged, so remove it from the
                    # remaining roles list to avoid removing it later.
                    index = current_role_ids.index(role.id)
                    current_role_ids.pop(index)
        return current_role_ids

    def _remove_roles_from_user(self, request, project_id, user_id,
                                current_role_ids):
        for id_to_delete in current_role_ids:
            api.keystone.remove_tenant_user_role(
                request,
                project=project_id,
                user=user_id,
                role=id_to_delete)

    def _is_removing_self_admin_role(self, request, project_id, user_id,
                                     available_roles, current_role_ids):
        is_current_user = user_id == request.user.id
        is_current_project = project_id == request.user.tenant_id
        available_admin_role_ids = [role.id for role in available_roles
                                    if role.name.lower() == 'admin']
        admin_roles = [role for role in current_role_ids
                       if role in available_admin_role_ids]
        if len(admin_roles):
            removing_admin = any([role in current_role_ids
                                  for role in admin_roles])
        else:
            removing_admin = False

        if is_current_user and is_current_project and removing_admin:
            # Cannot remove "admin" role on current(admin) project
            msg = _('You cannot revoke your administrative privileges '
                    'from the project you are currently logged into. '
                    'Please switch to another project with '
                    'administrative privileges or remove the '
                    'administrative role manually via the CLI.')
            messages.warning(request, msg)
            return True
        else:
            return False

    def _update_project_members(self, request, data, project_id):
        # update project members
        users_to_modify = 0
        # Project-user member step
        member_step = self.get_step(PROJECT_USER_MEMBER_SLUG)
        try:
            # Get our role options
            available_roles = self._get_available_roles(request)
            # Get the users currently associated with this project so we
            # can diff against it.
            users_roles = api.keystone.get_project_users_roles(
                request, project=project_id)
            users_to_modify = len(users_roles)

            for user_id in users_roles.keys():
                # Check if there have been any changes in the roles of
                # Existing project members.
                current_role_ids = list(users_roles[user_id])
                modified_role_ids = self._add_roles_to_users(
                    request, data, project_id, user_id,
                    current_role_ids, available_roles)
                # Prevent admins from doing stupid things to themselves.
                removing_admin = self._is_removing_self_admin_role(
                    request, project_id, user_id, available_roles,
                    modified_role_ids)
                # Otherwise go through and revoke any removed roles.
                if not removing_admin:
                    self._remove_roles_from_user(request, project_id, user_id,
                                                 modified_role_ids)
                users_to_modify -= 1

            # Grant new roles on the project.
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                # Count how many users may be added for exception handling.
                users_to_modify += len(data[field_name])
            for role in available_roles:
                users_added = 0
                field_name = member_step.get_member_field_name(role.id)
                for user_id in data[field_name]:
                    if user_id not in users_roles:
                        api.keystone.add_tenant_user_role(request,
                                                          project=project_id,
                                                          user=user_id,
                                                          role=role.id)
                    users_added += 1
                users_to_modify -= users_added
            return True
        except Exception:
            if PROJECT_GROUP_ENABLED:
                group_msg = _(", update project groups")
            else:
                group_msg = ""
            exceptions.handle(request,
                              _('Failed to modify %(users_to_modify)s'
                                ' project members%(group_msg)s and '
                                'update project quotas.')
                              % {'users_to_modify': users_to_modify,
                                 'group_msg': group_msg})
            return False

    def _update_project_groups(self, request, data, project_id, domain_id):
        # update project groups
        groups_to_modify = 0
        member_step = self.get_step(PROJECT_GROUP_MEMBER_SLUG)
        try:
            available_roles = self._get_available_roles(request)
            # Get the groups currently associated with this project so we
            # can diff against it.
            project_groups = api.keystone.group_list(request,
                                                     domain=domain_id,
                                                     project=project_id)
            groups_to_modify = len(project_groups)
            for group in project_groups:
                # Check if there have been any changes in the roles of
                # Existing project members.
                current_roles = api.keystone.roles_for_group(
                    self.request,
                    group=group.id,
                    project=project_id)
                current_role_ids = [role.id for role in current_roles]
                for role in available_roles:
                    # Check if the group is in the list of groups with
                    # this role.
                    field_name = member_step.get_member_field_name(role.id)
                    if group.id in data[field_name]:
                        # Add it if necessary
                        if role.id not in current_role_ids:
                            # group role has changed
                            api.keystone.add_group_role(
                                request,
                                role=role.id,
                                group=group.id,
                                project=project_id)
                        else:
                            # Group role is unchanged, so remove it from
                            # the remaining roles list to avoid removing it
                            # later.
                            index = current_role_ids.index(role.id)
                            current_role_ids.pop(index)

                # Revoke any removed roles.
                for id_to_delete in current_role_ids:
                    api.keystone.remove_group_role(request,
                                                   role=id_to_delete,
                                                   group=group.id,
                                                   project=project_id)
                groups_to_modify -= 1

            # Grant new roles on the project.
            for role in available_roles:
                field_name = member_step.get_member_field_name(role.id)
                # Count how many groups may be added for error handling.
                groups_to_modify += len(data[field_name])
            for role in available_roles:
                groups_added = 0
                field_name = member_step.get_member_field_name(role.id)
                for group_id in data[field_name]:
                    if not filter(lambda x: group_id == x.id,
                                  project_groups):
                        api.keystone.add_group_role(request,
                                                    role=role.id,
                                                    group=group_id,
                                                    project=project_id)
                    groups_added += 1
                groups_to_modify -= groups_added
            return True
        except Exception:
            exceptions.handle(request,
                              _('Failed to modify %s project '
                                'members, update project groups '
                                'and update project quotas.')
                              % groups_to_modify)
            return False

    def _update_project_quota(self, request, data, project_id):
        try:
            super(UpdateProject, self)._update_project_quota(
                request, data, project_id)
            return True
        except Exception:
            exceptions.handle(request, _('Modified project information and '
                                         'members, but unable to modify '
                                         'project quotas.'))
            return False

    def handle(self, request, data):
        # FIXME(gabriel): This should be refactored to use Python's built-in
        # sets and do this all in a single "roles to add" and "roles to remove"
        # pass instead of the multi-pass thing happening now.

        project = self._update_project(request, data)
        if not project:
            return False

        project_id = data['project_id']
        # Use the domain_id from the project if available
        domain_id = getattr(project, "domain_id", '')

        # update project details only if have perms
        if policy.check((('identity', 'identity:update_project'),), self.request, target={"project_id": project_id}):
            ret = self._update_project_members(request, data, project_id)
            if not ret:
                return False

            if PROJECT_GROUP_ENABLED:
                ret = self._update_project_groups(request, data,
                                                  project_id, domain_id)
                if not ret:
                    return False

            ret = self._update_project_quota(request, data, project_id)
            if not ret:
                return False

        return True
