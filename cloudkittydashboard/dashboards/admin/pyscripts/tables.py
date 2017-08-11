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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from horizon import tables

from cloudkittydashboard.api import cloudkitty as api


def get_detail_link(datum):
    if datum.script_id:
        url = "horizon:admin:pyscripts:script_details"
        return reverse(url, kwargs={'script_id': datum.script_id})


class CreatePyScript(tables.LinkAction):
    name = "createpyscript"
    verbose_name = _("Create Script")
    url = "horizon:admin:pyscripts:script_create"
    icon = "create"
    ajax = True
    classes = ("ajax-modal",)


class UpdateScript(tables.LinkAction):
    name = "updatepyscript"
    verbose_name = _("Edit Script")
    classes = ("ajax-modal",)
    icon = "pencil"

    def get_link_url(self, datum=None):
        url = "horizon:admin:pyscripts:script_update"
        return reverse(url, kwargs={'script_id': datum.script_id})


class DeletePyScript(tables.DeleteAction):
    name = "deletepyscript"
    verbose_name = _("Delete Script")
    action_present = _("Delete")
    action_past = _("Deleted")
    data_type_singular = _("PyScript")
    data_type_plural = _("PyScripts")
    icon = "remove"

    def action(self, request, script_id):
        api.cloudkittyclient(request).pyscripts.scripts.delete(
            script_id=script_id)


class PyScriptsTable(tables.DataTable):
    id = tables.Column("id", verbose_name=_("id"), link=get_detail_link)
    name = tables.Column("name", verbose_name=_("Name"))
    checksum = tables.Column("checksum", verbose_name=_("Checksum"))

    class Meta(object):
        name = "pyscripts"
        verbose_name = _("pyscripts")
        table_actions = (CreatePyScript, DeletePyScript)
        row_actions = (UpdateScript, DeletePyScript)
