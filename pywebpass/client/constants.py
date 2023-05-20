config_template = '''[API]

# Address to webserver location hosting webpass api
# WEBPASS_ADDRESS env can override this setting

# api_address = http://localhost:5000/webpass/api_address


# Password to use to connect to API server. THIS IS INSECURE!
# It is better to set an environment variable WEBPASS_PASSwD

# api_password = password


# By default, the client downloads the (still encrypted) database from the api and caches it.
# Setting this value to 'no' will force an api call for each query.
# Cache is in the form of encrypted KeePass (kdbx) files using the api server password.

  cache = yes

# Length of time in minutes before resyncing cache by default
# Units are "m"inutes, "h"ours, or "d"ays.

  cache_timeout = 1h

'''