# coding=utf-8
#
# File Name: _6000_zendesksupport.py
#
# Copyriht: 2016@nephoscale.com

from django.conf import settings

# The name of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = 'zendesk_support_dashboard'

# If set to True, this dashboard will not be added to the settings.
DISABLED = not getattr(settings, 'ZENDESKSUPPORT_ENABLED', True)

# A list of applications to be added to INSTALLED_APPS.
ADD_INSTALLED_APPS = [
    'openstack_dashboard.dashboards.zendesksupport',
]

# Adding js files
ADD_JS_FILES = [
    'dashboard/zendesksupport/jquery.nameBadges.js',
    'dashboard/zendesksupport/zendesksupport.js'
]

# Adding SAAS FILES
ADD_SCSS_FILES = ['dashboard/zendesksupport/zendesksupport.scss']

