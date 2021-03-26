"""
Main configuration file for the application

On deployment, desired configuration can be overridden by the provision of a local.cfg file
"""

##################################################
# overrides for the webapp deployment

DEBUG = True
"""is the web server in debug mode"""

PORT = 5027
"""port to start the webserver on"""

SSL = False
"""support SSL requests"""

THREADED = True
"""is the web server in threaded mode"""

############################################
# important overrides for the ES module

# elasticsearch back-end connection settings
ELASTIC_SEARCH_HOST = "http://gateway:9200"
"""base url to access elasticsearch"""

ELASTIC_SEARCH_INDEX = "jper"
"""index name in elasticsearch where our types are stored"""

ELASTIC_SEARCH_VERSION = "1.5.2"
"""version of elasticsearch which we're using - matters for certain semantics of requests"""

# Classes from which to retrieve ES mappings to be used in this application
# (note that if ELASTIC_SEARCH_DEFAULT_MAPPINGS is sufficient, you don't need to
# add anything here
ELASTIC_SEARCH_MAPPINGS = [
    # "service.dao.MyDAO"
]
"""type-specific mappings to be used when initialising - currently there are none"""

# initialise the index with example documents from each of the types
# this will initialise each type and auto-create the relevant mappings where
# example data is provided
ELASTIC_SEARCH_EXAMPLE_DOCS = [
    # "service.dao.MyDAO"
]
"""types which have their mappings initialised by example when initialising - currently there are none"""

############################################
# important overrides for account module

ACCOUNT_ENABLE = False
"""Disable user accounts"""

SECRET_KEY = "super-secret-key"
"""secret key for session management - only used when accounts are enabled"""

#############################################
# important overrides for storage module

STORE_IMPL = "octopus.modules.store.store.StoreLocal"
"""implementation class of the main fielstore"""

STORE_TMP_IMPL = "octopus.modules.store.store.TempStore"
"""implementation class of the temporary local filestore"""

from octopus.lib import paths
STORE_LOCAL_DIR = paths.rel2abs(__file__, "..", "service", "tests", "local_store", "live")
"""path to local directory for local file store - specified relative to this file"""

STORE_TMP_DIR = paths.rel2abs(__file__, "..", "service", "tests", "local_store", "tmp")
"""path to local directory for temp file store - specified relative to this file"""


#############################################
# Re-try/back-off settings

# from the http layer

# specific to this app

# Minimum amount to leave between attempts to deposit, in the event that there was a semi-permanent error
# default to 1 hour
LONG_CYCLE_RETRY_DELAY = 3600
"""Delay in between attempts to communicate with a repository that is failing, in seconds"""

# Maximum number of times to try and deposit before giving up and turning off repository sword submission
# for a given account
LONG_CYCLE_RETRY_LIMIT = 24
"""Number of re-try attempts against a failing repository before we give up"""

###############################################
## Other app-specific settings

DEFAULT_SINCE_DELTA_DAYS = 100
"""Number to substract from 'last_deposit_date' (safety margin) to get the date from which the first request against the JPER API will be made, in days"""

DEFAULT_SINCE_DATE = "1970-01-01T00:00:00Z"
"""The date from which the first request against the JPER API will be made when listing a repository's notifications"""

# how many seconds in between each run of the script
RUN_THROTTLE = 2
"""delay between executions of the deposit script, in seconds"""

# whether to store sword response data (receipt, etc).  Recommend only to store during testing operation
STORE_RESPONSE_DATA = False
"""Whether to store response data or not - set to True if testing"""
