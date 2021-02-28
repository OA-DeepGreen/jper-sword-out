"""
Tests on the repository activation/deactivation functions
"""

from standalone_octopus.modules.es.testindex import ESTestCase
from service import control, models
import time

class TestModels(ESTestCase):
    def setUp(self):
        super(TestModels, self).setUp()

    def tearDown(self):
        super(TestModels, self).tearDown()

    def test_01_activate_deactivate(self):
        # first, activation should create a status if none exists
        control.activate_deposit("123456789")

        time.sleep(2)

        rs = models.RepositoryStatus.pull("123456789")
        assert rs is not None
        assert rs.status == "succeeding"

        # now deactivate that account
        control.deactivate_deposit("123456789")

        time.sleep(2)

        rs = models.RepositoryStatus.pull("123456789")
        assert rs is not None
        assert rs.status == "failing"

        # now re-activate that account
        control.activate_deposit("123456789")

        time.sleep(2)

        rs = models.RepositoryStatus.pull("123456789")
        assert rs is not None
        assert rs.status == "succeeding"


