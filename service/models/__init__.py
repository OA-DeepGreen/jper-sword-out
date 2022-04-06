"""
This module contains all the model objects used by the system core.

All objects contained in sub-modules are also imported here, so that they can be imported elsewhere directly from this
module.

For example, instead of

::

    from service.models.account import Account
    from service.models.sword import RepositoryStatus

you can do

::

    from service.models import Account, RepositoryStatus

"""
from service.models.account import Account
from service.models.sword import RepositoryStatus, DepositRecord, RepositoryDepositLog
from service.models.requestnotification import RequestNotification