"""
This module contains all of the fixtures that are used throughout the testing.

The fixtures from each of the sub-modules are imported here for convenience, so instead of

::

    from service.tests.fixtures.notifications import NotificationFactory
    from service.tests.fixtures.sword import SwordFactory

you can do

::

    from service.tests.fixtures import NotificationFactory, SwordFactory
"""
from service.tests.fixtures.notifications import NotificationFactory
from service.tests.fixtures.sword import SwordFactory
from service.tests.fixtures.http_layer import MockHttpLayer
