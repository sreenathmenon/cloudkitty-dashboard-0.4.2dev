The openstack_dashboard/settings.py file must contain the following settings:

```
#Set Keystone Auth version
SC_AUTH_VERSION  = 2

#Set the Keystone authentication details
SC_USERNAME      = 'admin'
SC_PASSWORD      = 'password'

#Set the endpoint and authenticatiom urls like the following samples
SC_ENDPOINT      = 'http://198.100.181.74:9090/v2'
SC_AUTH_URL      = 'http://198.100.181.74:35357/v2.0'

#Set the endpoint type (Against which endpoint we need to check).In version 3, its internal, admin and public. In version 2.0 it is publicURL, adminURL, internalURL
SC_ENDPOINT_TYPE = 'publicURL'

#Set the region name (Against which region, the endpoint should be checked)
SC_REGION_NAME   = 'RegionOne'

#Set the project name
SC_TENANT_NAME   = 'admin'

#Set the maximum seconds to wait for the result
SC_TIMEOUT       = 10

#Set whether HTTPS should be verified or not
SC_INSECURE      = True

#Limit for the number of events to be displayed in the dashboard page
SC_DISPLAY_LIMIT = 15
```

The above settings are used to get an instance of sidecarclient for Creating and Listing of Events.
##### Files:-

1. events/tabs.py
2. events/views.py

