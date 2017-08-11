# coding=utf-8
#
# File Name: _7000_sidecar.py
#
# Copyriht: 2016@nephoscale.com

from django.conf import settings

# The name of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = 'sidecar_dashboard'

# If set to True, this dashboard will not be added to the settings.
DISABLED = not getattr(settings, 'SIDECAR_ENABLED', True)

# A list of applications to be added to INSTALLED_APPS.
ADD_INSTALLED_APPS = [
    'openstack_dashboard.dashboards.sidecar',
]

# Adding js files
ADD_JS_FILES = []

# Adding SAAS FILES
ADD_SCSS_FILES = [] 
