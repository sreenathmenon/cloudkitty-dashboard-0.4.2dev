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

from openstack_dashboard.dashboards.identity.billing.cipher import encrypt
from openstack_dashboard.local.local_settings import CIPHER_KEY

from openstack_dashboard.dashboards.identity.xprojects.ksclient import get_admin_ksclient

INDEX_URL = "horizon:identity:billing:index"
PROJECT_GROUP_ENABLED = keystone.VERSIONS.active >= 3
COMMON_HORIZONTAL_TEMPLATE = "identity/billing/_common_horizontal_form.html"


# helper to extract extra fields from data
def get_extra(request, data):
    extra = {}
    extra['address_street'] = data['address_street']
    extra['address_city'] = data['address_city']
    extra['address_state'] = data['address_state']
    extra['address_zip'] = data['address_zip']
    extra['address_country'] = data['address_country']
    # field 'billing_balance' should never be updated from this interface; skip it
    extra['billing_cc_holder'] = data['billing_cc_holder']
    extra['billing_cc_type'] = data['billing_cc_type']
    if data['billing_cc_number'][1] != '*':
        extra['billing_cc_number'] = encrypt(CIPHER_KEY, data['billing_cc_number'])
    extra['billing_cc_expire'] = data['billing_cc_expire']
    return extra

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
    address_street = forms.CharField(label=_("Street"), required=True)
    address_city = forms.CharField(label=_("City"), required=True)
    address_state = forms.CharField(label=_("State / Region"), required=True)
    address_zip = forms.CharField(label=_("ZIP Code"))
    address_country = forms.ChoiceField(label=_("Country"), choices=countries, initial='US', required=True)

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
        return values[0] + '/' + values[1]


cc_number_regexp="^(?:\*.*|4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})$"


class ProjectBillingAction(workflows.Action):
    billing_balance = forms.FloatField(label=_("Balance"), required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    billing_cc_holder = forms.CharField(label=_("Credit Card Holder"), required=True)
    billing_cc_type = forms.ChoiceField(label=_("Credit Card Type"), choices=cc_types, required=True)
    billing_cc_number = forms.RegexField(cc_number_regexp, label=_("Credit Card Number"), min_length=13, max_length=16, required=True)
    billing_cc_expire = CCExpireField(label=_("Credit Card Expire"), required=True)
    billing_cc_sec_code = forms.RegexField("^(?:\*.*|\d{3,4})$", label=_("CC Security Code"), min_length=3, max_length=4, required=False)

    def __init__(self, request, *args, **kwargs):
        super(ProjectBillingAction, self).__init__(request,
                                                 *args,
                                                 **kwargs)

    class Meta(object):
        name = _("Billing")


class ProjectBilling(workflows.Step):
    action_class = ProjectBillingAction
    template_name = COMMON_HORIZONTAL_TEMPLATE
    contributes = (
        "billing_balance",
        "billing_cc_holder",
        "billing_cc_type",
        "billing_cc_number",
        "billing_cc_expire",
        "billing_cc_sec_code"
    )


class UpdateBilling(workflows.Workflow):
    slug = "update_billing"
    name = _("Edit Project Billing Data")
    finalize_button_name = _("Save")
    success_message = _('Project billing data updated.')
    failure_message = _('Unable to modify project billing data.')
    success_url = "horizon:identity:billing:index"
    default_steps = (ProjectBilling, ProjectAddress)

    def __init__(self, request=None, context_seed=None, entry_point=None, *args, **kwargs):

        super(UpdateBilling, self).__init__(request=request,
                                            context_seed=context_seed,
                                            entry_point=entry_point,
                                            *args,
                                            **kwargs)

    def format_status_message(self, message):
        if "%s" in message:
            return message % self.context.get('name', 'unknown project')
        else:
            return message

    def handle(self, request, data):
        # update project info
        try:
            project_id = request.user.project_id
            extra = get_extra(request, data)
            # connect to keystone as 'billing' admin
            keystone = get_admin_ksclient()
            res = keystone.tenants.update(project_id, **extra)
            return res
        except Exception:
            exceptions.handle(request, ignore=True)
            return

        return True
