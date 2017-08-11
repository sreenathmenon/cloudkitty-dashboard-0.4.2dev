"""
table file
File: tabs.py
Description: tabs file 
Created On: 09-March-2016
Created By: binoy@nephoscale.com, murali@nephoscale.com
"""

#importing the packages
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tabs
from openstack_dashboard import api
from openstack_dashboard.dashboards.identity.invoice import tables
from cloudkittyclient import client
from cloudkittyclient.common import utils
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from openstack_dashboard.dashboards.identity.invoice import forms as project_forms
import json
import simplejson as json
import datetime
from cloudkittydashboard.api import cloudkitty as kittyapi
from collections import OrderedDict

#Defining the classes for action
#class for the tab listing  class objects
class Invoice:

    def __init__(self, info):
        self.id = info['invoice_id']
        self.name = info['invoice_id']
        self.tenant_name = info['tenant_name']
        self.paid_cost = info['paid_cost']
        self.balance_cost = info['balance_cost']
        self.total_cost = info['total_cost']
        self.invoice_date = info['invoice_date']
        self.tenant_id = info['tenant_id']
        self.invoice_period_from = info['invoice_period_from']
        self.invoice_period_to = info['invoice_period_to']
        self.payment_status = info['payment_status']

#class for the invoice tab
class InvoiceTab(tabs.TableTab):
    
    #Defining the class properties
    name = _("Instances Tab")
    slug = "instances_tab"
    table_classes = (tables.InvoicesTable,)
    template_name = ("horizon/common/_detail_table.html")
    preload = False


    def get_invoices_data(self):
        """
        Method: get_invoices_data
        desc: Method to get the data
        params:  self
        return: invoice dictionary
        """
        
        try:

            #Making the connection to the cloud kitty
            cloudkitty_conn = kittyapi.cloudkittyclient(self.request)
            
            #Getting the field name from the post
            field_name = self.request.POST.get('invoices__myfilter__q_field', 'default_value')
           
            #Searching with the posted values
            if field_name == 'invoice_id':
                invoices = cloudkitty_conn.reports.get_invoice(invoice_id=self.request.POST['invoices__myfilter__q'])
            elif field_name == 'payment_status':
            
                #Searching with the status values
                if self.request.POST['invoices__myfilter__q'].lower() == 'new':
                    invoices = cloudkitty_conn.reports.get_invoice(payment_status='0')
                elif self.request.POST['invoices__myfilter__q'].lower() == 'paid':
                    invoices = cloudkitty_conn.reports.get_invoice(payment_status='1')
                elif self.request.POST['invoices__myfilter__q'].lower() == 'declined':
                    invoices = cloudkitty_conn.reports.get_invoice(payment_status='2')
                elif self.request.POST['invoices__myfilter__q'].lower() == 'refunded':
                    invoices = cloudkitty_conn.reports.get_invoice(payment_status='3')
            elif field_name == 'tenant_id':
                invoices = cloudkitty_conn.reports.get_invoice(tenant_id=self.request.POST['invoices__myfilter__q'])
            else:
                
                #Getting the details for admin/ user
                if str(self.request.user) == 'admin':
                    invoices = cloudkitty_conn.reports.list_invoice(all_tenants='1')
                else:
                    invoices = cloudkitty_conn.reports.list_invoice()
            invoice_data = self.process_dict_and_display(invoices)
            return invoice_data
        except Exception:
            self._has_more = False
            error_message = _('Unable to get invoices')
            exceptions.handle(self.request, error_message)
            return []

    # Process invoice dict and display
    def process_dict_and_display(self, invoice):
        """
        Method: process_dict_and_display
        desc: Method to create the dictionary with the data available
        params:  self, invoice
        return: invoice dictionary
        """
        
        # Converting an Invoice Unicode to Dict
        invoice_details_full = invoice
        content = [] 
        
        # tenant based processing in invoicedata
        for tenant_data in invoice_details_full:

        	# Assigned necessary values for reusing the same
                info = {}
                info['invoice_date'] = tenant_data.invoice_date
                info['balance_cost'] = tenant_data.balance_cost
                info['tenant_name'] = tenant_data.tenant_name
                info['paid_cost'] = tenant_data.paid_cost
                info['total_cost'] = tenant_data.total_cost
                info['invoice_id'] = tenant_data.invoice_id
                info['tenant_id'] = tenant_data.tenant_id
                info['invoice_period_from'] = tenant_data.invoice_period_from
                info['invoice_period_to'] = tenant_data.invoice_period_to
                
                #Making the status to show
                info['payment_status'] = 'New'
                if tenant_data.payment_status == 1:
                    info['payment_status'] = 'Paid'
                elif tenant_data.payment_status == 2:
                    info['payment_status'] = 'Declined'
                elif tenant_data.payment_status == 3:
                    info['payment_status'] = 'Refunded'

                info['id'] = tenant_data.id
                content.append(Invoice(info))
        return content

#Invoice tab
class MyinvoiceTabs(tabs.TabGroup):
    
    #Defining the tab properties
    slug = "invoice_tabs"
    tabs = (InvoiceTab,)
    sticky = True

class MyinvoiceDetails(tabs.Tab):
    
    #Defining the tab properties
    name = _("Overview")
    slug = "overview"
    template_name = "identity/invoice/_detail_overview.html"

    def parseme(self, invoice_data):
        """
        Method: parseme
        desc: Method to make the table with price splitup
        params:  self, invoice_data
        return: price list
        """
        
        #Defining the list for price listing
        price_list = []
        
        for invoice_data in invoice_data:
            
            invoice_data = invoice_data.invoice_data
      
	    # for proper sorting as needed 
	    keyorder = {k:v for v,k in enumerate(['dict_all_cost_total', 'dict_total_all', 'dict_compute', 'dict_image_snapshot', 'dict_volume', 'dict_inbound', 'dict_outbound', 'dict_floating', 'dict_cloud_storage', 'dict_instance_addon', 'dict_tenant_addon'])}
	    invoice_data = OrderedDict(sorted(invoice_data.items(), key=lambda i:keyorder.get(i[0])))
 
            # itemized Invoice details of the particular tenant
            for invoice_data_entity, value in invoice_data.iteritems():
   
                # Invoice_data_entity details
                # For make user to understand the case well
                invoice_data_entity_list = {'dict_all_cost_total': 'Total Cost for Tenant based on all Instances',
                                            'dict_total_all': 'Total Cost for Instance',
					    'dict_compute': 'Compute Cost for Instance',
					    'dict_image_snapshot': 'Image Cost',
					    'dict_volume': 'Block Storage(Volume)',
                                            'dict_inbound': 'Network Transfer (inbound) for Instance',
					    'dict_outbound': 'Network Transfer (outbound) for Instance',
                                            'dict_floating': 'Floating IP Addresses',
                                            'dict_cloud_storage': 'Object Storage (Swift)',
					    'dict_instance_addon': 'Compute Instance Add-On',
					    'dict_tenant_addon': 'Project Add-On',}
    
                # If value is Dict (Itemized invoice)
                if type(value) is dict:
    
                    # get the instance id and other instance and cost details
                    for instance_id, details in value.iteritems():
    
                        # variables for necessary items
                        entity_name = invoice_data_entity_list[invoice_data_entity]
                        instance_id = instance_id
                        instance_name = details[0]
                        instance_size = details[1]
                        cost = details[2]
                        
                        # field names and add values to rows
                        price_data = {}
                        price_data['entity_name'] = entity_name
                        price_data['instance_id'] = instance_id
                        price_data['instance_name'] = instance_name
                        price_data['instance_size'] = instance_size
                        price_data['cost'] = cost
                        price_list.append(price_data)
                else:
                    
                    # variables for necessary items
                    entity_name = invoice_data_entity_list[invoice_data_entity]
                    cost = value
    
                    # field names and add values to rows
                    price_data = {}
                    price_data['entity_name'] = entity_name
                    price_data['instance_id'] = '-'
                    price_data['instance_name'] = '-'
                    price_data['instance_size'] = '-'
                    price_data['cost'] = cost
                    price_list.append(price_data)
            return price_list


    def get_context_data(self, request):
        """
        Method: parseme
        desc: Method to make the table with price splitup
        params:  self, invoice_data
        return: price list
        """
        
        try:
	    #Get the details of invoice
            invoice = self.tab_group.kwargs['invoice']
            invoice_data = invoice
            price_data = self.parseme(invoice_data)
            return {"invoice": invoice, 'price_value': price_data}
	except Exception:
            exceptions.handle(self.request, _("Unable to retrieve invoice details."))
    	    return {"invoice": {}, 'price_value': {}}
 
class MyinvoiceDetailsTabs(tabs.TabGroup):
    
    # Setting the invoice detail properties
    slug = "invoice_tabs"
    tabs = (MyinvoiceDetails,)
    sticky = True
