# Copyright 2015 Objectif Libre
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

from django.conf.urls import patterns
from django.conf.urls import url

from cloudkittydashboard.dashboards.admin.pyscripts import views

urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create/?$', views.ScriptCreateView.as_view(), name="script_create"),
    url(r'^update/(?P<script_id>[^/]+)/?$', views.ScriptUpdateView.as_view(),
        name="script_update"),
    url(r'^(?P<script_id>[^/]+)/?$', views.ScriptDetailsView.as_view(),
        name="script_details"),
    )
