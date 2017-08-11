"""
view file
File: forms.py
Description: Form for the update  
Created On: 09-March-2016
Created By: binoy@nephoscale.com, murali@nephoscale.com
"""

#importing the packages
import decimal
from horizon import forms
from horizon import exceptions
from cloudkittyclient import client
from cloudkittydashboard.api import cloudkitty as kittyapi
from django.utils.translation import ugettext_lazy as _

#update invoice class
class UpdateInvoice(forms.SelfHandlingForm):
    
    #Defining the form fields
    invoice_id = forms.CharField(label=_("Invoice ID"),  widget=forms.TextInput(attrs={'readonly':'readonly'}), required=False)
    paid_cost = forms.DecimalField(label=_("Paid  Cost"), min_value=0, max_digits=32, decimal_places=2)
    balance_cost = forms.DecimalField(label=_("Balance  Cost"), min_value=0, max_digits=32, decimal_places=2)
    paid_status = (('0', 'New'), ('1', 'Paid'), ('2', 'Declined'), ('3', 'Refunded'))
    payment_status = forms.ChoiceField(choices=paid_status, required=True )

    def handle(self, request, data):
        """
        method : handle
        desc: To handle the update
        params:
            self - self
            request - request data
            data - update datas
        return: Update o/p
        """
        
        try:
            
            #Making the connection with the cloudkitty
            cloudkitty_conn = kittyapi.cloudkittyclient(self.request)
            
            #updating the invoice
            invoice = cloudkitty_conn.reports.update_invoice(
                           invoice_id     = data['invoice_id'],
                           payment_status = str(data['payment_status']),
                           paid_cost      = str(data['paid_cost']),
                           balance_cost   = str(data['balance_cost']))
                           
            return invoice
        except Exception:
            exceptions.handle(request, _('Unable to update invoice.'))
