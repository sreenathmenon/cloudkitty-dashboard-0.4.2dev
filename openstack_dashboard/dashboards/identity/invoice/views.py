"""
view file
File: view.py
Description: Logic comes 
Created On: 09-March-2016
Created By: binoy@nephoscale.com, murali@nephoscale.com
"""

#importing the packages
from horizon import tabs
from openstack_dashboard.dashboards.identity.invoice import tabs as identity_tabs
import json
from cloudkittyclient import client
from cloudkittyclient.common import utils
import ConfigParser
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from openstack_dashboard import api
from openstack_dashboard.dashboards.identity.invoice import forms as project_forms
from openstack_dashboard.dashboards.identity.invoice import tables as invoice_tables
import simplejson as json
import datetime
from cloudkittydashboard.api import cloudkitty as kittyapi


#Class for the tabbed table view
class IndexView(tabs.TabbedTableView):
    
    #Setting the properties
    tab_group_class = identity_tabs.MyinvoiceTabs
    template_name = 'identity/invoice/index.html'
     
#Class for the update invoice
class UpdateInvoiceView(forms.ModalFormView):
    
    #Setting the properties
    form_class = project_forms.UpdateInvoice
    template_name = 'identity/invoice/update_invoice.html'
    success_url = reverse_lazy("horizon:identity:invoice:index")
    modal_id = "create_snapshot_modal"
    modal_header = _("Update Invoice")
    submit_label = _("Update Invoice")
    submit_url = "horizon:identity:invoice:update_invoice"

    @memoized.memoized_method
    def get_object(self):
        """
        Method: get_object
        Desc: Getting the object details
        Params: self
        Return: Class objects
        """

        try:

            #Making the cloudkitty connection
            cloudkitty_conn = kittyapi.cloudkittyclient(self.request)
            
            #Getting the invoice data
            invoice = cloudkitty_conn.reports.get_invoice(invoice_id=self.kwargs["invoice_id"])
            
            #Making the invoice data type to json
            invoice_details_full = invoice

	    return(invoice_details_full)

        except Exception:
            exceptions.handle(self.request, _("Unable to retrieve invoices."))

    def get_initial(self):
        """
        Method: get_initial
        Desc: Getting the object details to show in the update form
        Params: self
        Return: data dictionary
        """
        
        #Getting the object details to show in the update form
        invoices = self.get_object()
	
	for datas in invoices:

		invoice_id = datas.invoice_id
		tenant_name = datas.tenant_name
		total_cost = datas.total_cost
		balance_cost = datas.balance_cost
		paid_cost = datas.paid_cost
		payment_status = datas.payment_status
	
 
        #Setting the data to show in update form
        data = {'invoice_id': invoice_id,
                'tenant_name': tenant_name, 
                'total_cost': total_cost,
                'balance_cost': balance_cost,
                'paid_cost': paid_cost,
                'payment_status': payment_status}
        return data

    def get_context_data(self, **kwargs):
        """
        Method: get_context_data
        Desc: Setting the context data
        Params: self, 
            wargs: details if the invoice
        Return: context
        """
        
        #Setting the context
        context = super(UpdateInvoiceView, self).get_context_data(**kwargs)
        invoice_id = self.kwargs['invoice_id']
        context['invoice_id'] = invoice_id
        context['invoice'] = self.get_object()
        context['submit_url'] = reverse(self.submit_url, args=[invoice_id])
        return context

#Class for the detailed view
class DetailInvoiceView(tabs.TabView):
    
    #Setting the properties
    tab_group_class = identity_tabs.MyinvoiceDetailsTabs
    template_name = 'identity/invoice/details.html'
    page_title = _("Invoice Details: {{ invoice.name }}")
    
    def get_context_data(self, **kwargs):
        """
        Method: get_context_data
        Desc: Setting the context data
        Params: self, 
            wargs: details if the invoice
        Return: context
        """
        
	#Setting the context
        context = super(DetailInvoiceView, self).get_context_data(**kwargs)

	try:
	    invoice = self.get_data()
            table = invoice_tables.InvoicesTable(self.request)
            context["invoice"] = invoice
            context["url"] = self.get_redirect_url()
            return context
	except Exception:
            exceptions.handle(self.request, _("No invoice data for the available invoice id here."))
	    return context

    @staticmethod
    def get_redirect_url():
        """
        Method: get_redirect_url
        Desc: Getting the redirect url
        Params: NA
        Return: detail url
        """
        
        #getting the redirect url
        return reverse_lazy('horizon:identity:invoice:detail_invoice')

    @memoized.memoized_method
    def get_data(self):
        """
        Method: get_data
        Desc: Getting the data
        Params: self
        Return: invoice data (dictionary)
        """
  
	invoice_data = '' 
    	try:        
	    #connecting to the cloudkitty api and getting the invoice details
            cloudkitty_conn = kittyapi.cloudkittyclient(self.request)
            invoice = cloudkitty_conn.reports.get_invoice(invoice_id=self.kwargs['id'])
            return invoice
	except Exception:
            exceptions.handle(self.request, _("No invoice data for the available invoice id."))
	    return invoice_data

    def get_tabs(self, request, *args, **kwargs):
        """
        Method: get_tabs
        Desc: Getting the tab to show the details
        Params: self, request, *args, **kwargs(invoice details)
        Return: tab with details
        """
       	try: 
            invoice = self.get_data()
            return self.tab_group_class(request, invoice=invoice, **kwargs)
	except Exception:
            exceptions.handle(self.request, _("No invoice data for the available invoice id."))
