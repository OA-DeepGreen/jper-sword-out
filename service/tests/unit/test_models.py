"""
Tests on the models
"""

from standalone_octopus.modules.es.testindex import ESTestCase
from service import models
from service.tests import fixtures
from standalone_octopus.lib import dataobj, dates
import time

class TestModels(ESTestCase):
    def setUp(self):
        super(TestModels, self).setUp()

    def tearDown(self):
        super(TestModels, self).tearDown()

    def test_01_account(self):
        # first load some accounts into the system, some with and some without sword support
        acc1 = models.Account()
        acc1.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc1.save()

        acc2 = models.Account()
        acc2.add_sword_credentials("acc2", "pass2", "http://sword/2")
        acc2.save()

        acc3 = models.Account()
        acc3.save()

        acc4 = models.Account()
        acc4.save(blocking=True)

        time.sleep(2)

        accs = models.Account.with_sword_activated()
        assert len(accs) == 2
        for acc in accs:
            assert acc.sword_collection in ["http://sword/1", "http://sword/2"]

    def test_02_repository_status(self):
        # make a blank one
        rs = models.RepositoryStatus()

        # test all its methods
        dataobj.test_dataobj(rs, fixtures.SwordFactory.repository_status_do_test())

        # make a new one around some existing data
        rs = models.RepositoryStatus(fixtures.SwordFactory.repository_status())

        # try recording a failure which increments the counter
        lt = rs.last_tried
        rs.record_failure(24)
        assert rs.last_tried != lt
        assert rs.retries == 15
        assert rs.status == "problem"

        # now try incrementing the counter past the limit
        rs.record_failure(15)
        assert rs.last_tried is None
        assert rs.retries == 0
        assert rs.status == "failing"

        # now record a new failure and check that we can't retry straight away
        rs.record_failure(10)
        assert not rs.can_retry(100)

        # now check that once the delay is over we can retry
        time.sleep(2)
        assert rs.can_retry(1)

        # try deleting the last_tried date directly
        assert rs.last_tried is not None
        del rs.last_tried
        assert rs.last_tried is None

        # try deactivating and activating the status
        rs.activate()
        assert rs.status == "succeeding"
        assert rs.retries == 0

        rs.deactivate()
        assert rs.status == "failing"


    def test_03_deposit_record(self):
        # make a blank one
        dr = models.DepositRecord()

        # test all its methods
        dataobj.test_dataobj(dr, fixtures.SwordFactory.deposit_record_do_test())

        # make a new one around some existing data
        dr = models.DepositRecord(fixtures.SwordFactory.deposit_record())

        # check the was_successful calculations
        # when the metadata fails, that is a certain failure irrespective of the other values
        dr.metadata_status = "failed"
        dr.content_status = "deposited"
        dr.completed_status = "deposited"
        assert not dr.was_successful()

        # accross the board success
        dr.metadata_status = "deposited"
        dr.content_status = "deposited"
        dr.completed_status = "deposited"
        assert dr.was_successful()

        # failed at the complete stage
        dr.metadata_status = "deposited"
        dr.content_status = "deposited"
        dr.completed_status = "failed"
        assert not dr.was_successful()

        # failed at the content stage
        dr.metadata_status = "deposited"
        dr.content_status = "failed"
        dr.completed_status = "deposited"
        assert not dr.was_successful()

        # successful metadata-only deposit
        dr.metadata_status = "deposited"
        dr.content_status = "none"
        dr.completed_status = "none"
        assert dr.was_successful()

    def test_04_deposit_record_pull(self):
        dd = dates.now()

        # create a deposit record with some properties we can check
        dr = models.DepositRecord()
        dr.notification = "123456"
        dr.repository = "abcdef"
        dr.metadata_status = "deposited"
        dr.content_status = "deposited"
        dr.completed_status = "failed"
        dr.deposit_date = dd
        dr.save(blocking=True)

        # first check an empty response
        r = models.DepositRecord.pull_by_ids("adfsadf", "kasdfasf")
        assert r is None

        # now check we can retrieve the real thing
        r = models.DepositRecord.pull_by_ids("123456", "abcdef")
        assert r.notification == "123456"
        assert r.repository == "abcdef"
        assert r.metadata_status == "deposited"
        assert r.content_status == "deposited"
        assert r.completed_status == "failed"
        assert r.deposit_date == dd

