# _______________________________________________________________________
# | File Name: forms.py                                                 |
# |                                                                     |
# | This file is for handling the forms of zendesk support              |
# |_____________________________________________________________________|
# | Start Date: July 7th, 2016                                          |
# |                                                                     |
# | Package: Openstack Horizon Dashboard [liberity]                     |
# |                                                                     |
# | Copy Right: 2016@nephoscale                                         |
# |_____________________________________________________________________|

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django  import forms as django_forms
from horizon import exceptions
from horizon import forms
from openstack_dashboard.dashboards.zendesksupport import api as zendesk_api
from django.shortcuts import render, redirect
from openstack_dashboard import api

#Setting the ticket priority choices
TICKET_PRIORITY_CHOICES = (
    ('low',    'Low'),
    ('normal', 'Normal'),
    ('high',   'High'),
    ('urgent', 'Urgent')
)

class BaseUserForm(forms.SelfHandlingForm):
    def __init__(self, request, *args, **kwargs):
        super(BaseUserForm, self).__init__(request, *args, **kwargs)

        # Populate project choices
        user_choices = []

        # If the user is already set (update action), list only projects which
        # the user has access to.
        users = api.keystone.user_list(request)
        for user in users:
            
            #Checking the user have email
            has_email = hasattr(user,  'email')
            if user.enabled and user.id != request.user.id and has_email:
                
                #Only users with an email will be listed in the dropdown
                if getattr(user, 'email') != '':

                    #Creating the dropdown value (user id, email and name)
                    user_value = str(user.id) + '--' +  str(user.email) + '--' + str(user.name)
                    user_choices.append((user_value, user.name))

                #Creating the dropdown value (user id, email and name)
                user_value = str(user.id) + '--' +  str(user.email) + '--' + str(user.name)
                user_choices.append((user_value, user.name))
                
        #to show the drop down first element.
        if not user_choices:
            user_choices.insert(0, ('', _("No available users")))
        elif len(user_choices) > 1:
            user_choices.insert(0, ('', _("Select a user")))
        self.fields['user'].choices = user_choices

class CreateTicketForm(BaseUserForm):
    """
    # | Form Class to handel the ticket create form
    """
    
    #Creating the fields
    subject     = forms.CharField(  label=_("Subject of your issue"), required=True,  widget=forms.TextInput)
    priority    = forms.ChoiceField(label=_("Priority"),              required=True,  widget=forms.Select,   choices=TICKET_PRIORITY_CHOICES)
    description = forms.CharField(  label=_("Describe your issue"),   required=True,  widget=forms.Textarea ) 
    #attachments = forms.FileField(  label=_("Attachments"),           required=False, widget=forms.ClearableFileInput(attrs={'multiple': True}))
    user = forms.DynamicChoiceField(label=_("User list"), required=False,)

    def handle(self, request, data):
        """ 
        * Form to handel the create ticket request
        *
        * @Arguments:
        *   <request>: Request object
        *   <data>:    Data containg form data
        """
        subject     = data['subject']
        description = data['description']
        priority    = data['priority']
        user        = data['user']
        #files       = request.FILES.getlist('attachments')

        # Okay, now we need to call our zenpy to create the 
        # ticket, with admin credential, on behalf of user
        try:
            zendesk = zendesk_api.Zendesk(self.request)
            # First if there is any file, then we need to
            # attach those
            # Currently our zenpy object is not supporting 
            # attachment. Need to decide later
            #if len(files):
            #    for f in files:
            #        zendesk.create_attachment(f)
            #        #f.save()
            #        print f.__dict__
            
            api_data = {
                "subject": subject,
                "priority": priority,
                "description": description,
                "user": user
            }
            
            #Calling the method to create the tickets
            ticket_audit = zendesk.create_ticket(api_data, request)
            ticket = ticket_audit.ticket
            return redirect(reverse_lazy("horizon:zendesk_support_dashboard:tickets:ticket_detail", args=[ticket.id]))
        except Exception as err:
            error_message = _(str(err))
            exceptions.handle(request, error_message)
            return []

class AddCommentForm(django_forms.Form):
    """
    | * Class to add the comments to thye tickets
    """
    comment = forms.CharField(label = _('Add Comment'), required=True, widget=forms.TextInput)
