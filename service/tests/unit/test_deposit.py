"""
Tests on the deposit functions
"""

from standalone_octopus.modules.es.testindex import ESTestCase
from service import deposit, models
from standalone_octopus.modules.jper import client
from standalone_octopus.modules.jper import models as jmod
from standalone_octopus.modules.store import store
from service.tests import fixtures
from standalone_octopus.lib import dates, http
from standalone_octopus.modules.swordv2 import client_http
import time, sword2, urllib.parse, json, os, zipfile
from io import StringIO
from standalone_octopus.core import app


def mock_process_account_fail(*args, **kwargs):
    raise client.JPERException("oops")

def mock_process_notification_fail(*args, **kwargs):
    raise deposit.DepositException


def mock_process_notification_success(*args, **kwargs):
    pass


def mock_metadata_deposit_fail(*args, **kwargs):
    raise deposit.DepositException()

def mock_metadata_deposit_success(*args, **kwargs):
    dr = sword2.Deposit_Receipt()
    return dr

def mock_package_deposit_fail(*args, **kwargs):
    raise deposit.DepositException()

def mock_package_deposit_success(*args, **kwargs):
    pass


def mock_complete_deposit_fail(*args, **kwargs):
    raise deposit.DepositException()

def mock_complete_deposit_success(*args, **kwargs):
    pass


def mock_get_content(url, *args, **kwargs):
    with open(fixtures.NotificationFactory.example_package_path()) as f:
        cont = f.read()
    return http.MockResponse(200, cont), "", 0

def mock_iterate_fail(*args, **kwargs):
    raise client.JPERException()

def mock_iterate_success(self, since, *args, **kwargs):
    nl = fixtures.NotificationFactory.notification_list(since, page=1, pageSize=2, count=4, ids=["1111", "2222"])
    for n in nl.get("notifications"):
        yield jmod.OutgoingNotification(n)


class TestDeposit(ESTestCase):
    def setUp(self):
        super(TestDeposit, self).setUp()

        self.old_process_notification = deposit.process_notification
        self.old_process_account = deposit.process_account

        self.old_metadata_deposit = deposit.metadata_deposit
        self.old_package_deposit = deposit.package_deposit
        self.old_complete_deposit = deposit.complete_deposit
        self.old_http_get_stream = http.get_stream

        self.old_iterate = client.JPER.iterate_notifications

        self.old_octopus_http = client_http.OctopusHttpLayer

        self.stored_ids = []

        self.retry_delay = app.config.get("LONG_CYCLE_RETRY_DELAY")
        self.retry_limit = app.config.get("LONG_CYCLE_RETRY_LIMIT")

    def tearDown(self):
        deposit.process_notification = self.old_process_notification
        deposit.process_account = self.old_process_account

        deposit.metadata_deposit = self.old_metadata_deposit
        deposit.package_deposit = self.old_package_deposit
        deposit.complete_deposit = self.old_complete_deposit
        http.get_stream = self.old_http_get_stream

        client.JPER.iterate_notifications = self.old_iterate

        client_http.OctopusHttpLayer = self.old_octopus_http

        app.config["LONG_CYCLE_RETRY_DELAY"] = self.retry_delay
        app.config["LONG_CYCLE_RETRY_LIMIT"] = self.retry_limit

        tmp = store.StoreFactory.tmp()
        for sid in self.stored_ids:
            tmp.delete(sid)

        super(TestDeposit, self).tearDown()

    def test_01_run_fail(self):
        # create a process_account method that will fail
        deposit.process_account = mock_process_account_fail

        # load some accounts into the index
        acc1 = models.Account()
        acc1.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc1.save()

        acc2 = models.Account()
        acc2.add_sword_credentials("acc2", "pass2", "http://sword/2")
        acc2.save(blocking=True)

        # with fail on error
        with self.assertRaises(client.JPERException):
            deposit.run(True)

        # and without fail on error
        deposit.run(False)

    def test_02_notification_ignore(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_fail
        deposit.package_deposit = mock_package_deposit_fail
        deposit.complete_deposit = mock_complete_deposit_fail

        # get a since date, doesn't really matter what it is
        since = dates.now()

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.save()

        # create a notification with the analysis date the same as the since date
        source = fixtures.NotificationFactory.outgoing_notification()
        source["analysis_date"] = since
        note = jmod.OutgoingNotification(source)

        # make a deposit record for the notification
        dr = models.DepositRecord()
        dr.notification = note.id
        dr.repository = acc.id
        dr.deposit_date = dates.format(dates.before_now(3600))
        dr.metadata_status = "deposited"
        dr.content_status = "none"
        dr.completed_status = "none"
        dr.save(blocking=True)

        # now process the notification, which we expect to ignore this one
        deposit.process_notification(acc, note, since)

        # the mocks will cause the above to throw an error if it gets to processing the
        # results, so this test doesn't need assertions

        # now just to check that if the since date is different, or there is no deposit record,
        # processing continues as expected

        # if the since date is not the same, it shouldn't even look to see if it's been deposited before
        ago = dates.format(dates.before_now(100000))
        with self.assertRaises(deposit.DepositException):   # because this is what the mock does if it gets called
            deposit.process_notification(acc, note, ago)

        # if there's no deposit record
        dr.delete()
        time.sleep(2)

        with self.assertRaises(deposit.DepositException):   # because this is what the mock does if it gets called
            deposit.process_notification(acc, note, since)

    def test_03_notification_metadata_fail(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_fail
        deposit.package_deposit = mock_package_deposit_fail
        deposit.complete_deposit = mock_complete_deposit_fail

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        with self.assertRaises(deposit.DepositException):   # because this is what the mock does if it gets called
            deposit.process_notification(acc, note, since)

        time.sleep(2)

        # nonetheless, this should create a deposit record
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        assert dr is not None
        assert dr.notification == note.id
        assert dr.repository == acc.id
        assert dr.deposit_datestamp >= dates.parse(since)
        assert dr.metadata_status == "failed"
        assert dr.content_status is None            # because there /is/ content, but we wouldn't have got that far
        assert dr.completed_status is None

    def test_04_notification_metadata_no_package_success(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_success
        deposit.package_deposit = mock_package_deposit_fail
        deposit.complete_deposit = mock_complete_deposit_fail

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification without any links in it
        source = fixtures.NotificationFactory.outgoing_notification()
        source["links"] = []
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        # process the notification, which we expect to go without error
        deposit.process_notification(acc, note, since)

        time.sleep(2)

        # this should have created a deposit record
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        assert dr is not None
        assert dr.notification == note.id
        assert dr.repository == acc.id
        assert dr.deposit_datestamp >= dates.parse(since)
        assert dr.metadata_status == "deposited"
        assert dr.content_status == "none"
        assert dr.completed_status == "none"

    def test_05_cache_content(self):
        # specify the mock for the http.get function
        http.get_stream = mock_get_content

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification without any links in it
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # extract the specific link we want to test with
        link = note.get_package_link("http://purl.org/net/sword/package/SimpleZip")

        # technically this is a private method, but it does a single key bit of
        # work so is worth testing it in isolation
        local_id, path = deposit._cache_content(link, note, acc)
        self.stored_ids.append(local_id)

        # now check the things we know about the cached content
        #
        # check the return values
        assert os.path.exists(path)
        assert os.path.isfile(path)
        assert local_id is not None

        # check the tmp store
        tmp = store.StoreFactory.tmp()
        assert tmp.exists(local_id)
        files = tmp.list(local_id)
        assert files >= 1
        assert "SimpleZip" in files

        # check the content in the store
        stream = tmp.get(local_id, "SimpleZip")
        z = zipfile.ZipFile(stream)
        assert z is not None

    def test_06_metadata_success_package_fail(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_success
        deposit.package_deposit = mock_package_deposit_fail
        deposit.complete_deposit = mock_complete_deposit_fail

        # specify the mock for the http.get function
        http.get_stream = mock_get_content

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification and keep the links
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        # process the notification, which should throw an exception at the package deposit stage
        with self.assertRaises(deposit.DepositException):
            deposit.process_notification(acc, note, since)

        time.sleep(2)

        # this should have created a deposit record
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        assert dr is not None
        assert dr.notification == note.id
        assert dr.repository == acc.id
        assert dr.deposit_datestamp >= dates.parse(since)
        assert dr.metadata_status == "deposited"
        assert dr.content_status == "failed"
        assert dr.completed_status is None

        # ensure that the tmp directory is cleared out
        tmp = store.StoreFactory.tmp()
        dirs = [x for x in os.listdir(tmp.dir) if os.path.isdir(os.path.join(tmp.dir, x))]
        assert len(dirs) == 0

    def test_07_metadata_success_package_success_complete_fail(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_success
        deposit.package_deposit = mock_package_deposit_success
        deposit.complete_deposit = mock_complete_deposit_fail

        # specify the mock for the http.get function
        http.get_stream = mock_get_content

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification and keep the links
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        # process the notification, which should throw an exception at the final stage
        with self.assertRaises(deposit.DepositException):
            deposit.process_notification(acc, note, since)

        time.sleep(2)

        # this should have created a deposit record
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        assert dr is not None
        assert dr.notification == note.id
        assert dr.repository == acc.id
        assert dr.deposit_datestamp >= dates.parse(since)
        assert dr.metadata_status == "deposited"
        assert dr.content_status == "deposited"
        assert dr.completed_status == "failed"

        # ensure that the tmp directory is cleared out
        tmp = store.StoreFactory.tmp()
        dirs = [x for x in os.listdir(tmp.dir) if os.path.isdir(os.path.join(tmp.dir, x))]
        assert len(dirs) == 0

    def test_08_full_deposit_success(self):
        # set up the mocks, so that nothing can happen, even if the test goes wrong
        deposit.metadata_deposit = mock_metadata_deposit_success
        deposit.package_deposit = mock_package_deposit_success
        deposit.complete_deposit = mock_complete_deposit_success

        # specify the mock for the http.get function
        http.get_stream = mock_get_content

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification and keep the links
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        # process the notification, which we expect to go without error
        deposit.process_notification(acc, note, since)

        time.sleep(2)

        # this should have created a deposit record
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        assert dr is not None
        assert dr.notification == note.id
        assert dr.repository == acc.id
        assert dr.deposit_datestamp >= dates.parse(since)
        assert dr.metadata_status == "deposited"
        assert dr.content_status == "deposited"
        assert dr.completed_status == "deposited"

        # ensure that the tmp directory is cleared out
        tmp = store.StoreFactory.tmp()
        dirs = [x for x in os.listdir(tmp.dir) if os.path.isdir(os.path.join(tmp.dir, x))]
        assert len(dirs) == 0

    def test_09_process_account_failing(self):
        # set up a mock that will fail if the function is called - we shouldn't get that far in this test
        deposit.process_notification = mock_process_notification_fail

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # set a repository status object that tells us the repo is failing
        rs = models.RepositoryStatus()
        rs.id = acc.id
        rs.status = "failing"
        rs.save(blocking=True)

        # this should just run and return straight away
        deposit.process_account(acc)

        # nothing we can really test here, nothing has changed - if we don't get an exception the
        # test is passed

        # now set the status to "problem" but with a timeout that has not yet passed
        rs.record_failure(10)
        app.config["LONG_CYCLE_RETRY_DELAY"] = 100  # just to make sure it doesn't expire

        # this should just run and return straight away
        deposit.process_account(acc)

        # nothing we can really test here, nothing has changed - if we don't get an exception the
        # test is passed

    def test_10_process_account_jper_error(self):
        # make the iterator on JPER fail immediately
        client.JPER.iterate_notifications = mock_iterate_fail

        # just to prevent anything happening if the test is broken
        deposit.process_notification = mock_process_notification_success

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # this should just run and give us the JPER exception
        with self.assertRaises(client.JPERException):
            deposit.process_account(acc)

        time.sleep(2)

        # there was no status object, so one should have been created
        status = models.RepositoryStatus.pull(acc.id)
        assert status is not None
        assert status.status == "succeeding"
        assert status.last_deposit_date == app.config.get("DEFAULT_SINCE_DATE")
        assert status.retries == 0
        assert status.last_tried is None

    def test_11_process_account_error(self):
        # make the iterator on JPER give us mock responses
        client.JPER.iterate_notifications = mock_iterate_success

        # set up a mock that will fail when the function is called, to trigger the account failure
        deposit.process_notification = mock_process_notification_fail

        app.config["LONG_CYCLE_RETRY_DELAY"] = 0  # so we don't have to wait
        app.config["LONG_CYCLE_RETRY_LIMIT"] = 10  # so we know exactly how many

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # this should bring us to the brink of failure, but not quite over the edge
        for i in range(10):
            deposit.process_account(acc)

        time.sleep(2)

        # there was no status object, so one should have been created, which we can check for suitable properties
        status = models.RepositoryStatus.pull(acc.id)
        assert status is not None
        assert status.status == "problem"
        assert status.last_deposit_date == app.config.get("DEFAULT_SINCE_DATE")
        assert status.retries == 10
        assert status.last_tried is not None

        # now one final request should tip it over the edge, and it will start failing
        deposit.process_account(acc)

        time.sleep(2)

        # now look for the updated status object which should be set to "failing" mode
        status = models.RepositoryStatus.pull(acc.id)
        assert status is not None
        assert status.status == "failing"
        assert status.last_deposit_date == app.config.get("DEFAULT_SINCE_DATE")
        assert status.retries == 0
        assert status.last_tried is None

    def test_12_process_account_success(self):
        # make the iterator on JPER give us mock responses
        client.JPER.iterate_notifications = mock_iterate_success

        # set up a mock that will fail when the function is called, to trigger the account failure
        deposit.process_notification = mock_process_notification_success

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        deposit.process_account(acc)

        time.sleep(2)

        # there was no status object, so one should have been created, which we can check for suitable properties
        status = models.RepositoryStatus.pull(acc.id)
        assert status is not None
        assert status.status == "succeeding"
        assert status.last_deposit_date == "2015-02-02T00:00:00Z"
        assert status.retries == 0
        assert status.last_tried is None

    def test_12_broken_repository(self):
        client_http.OctopusHttpLayer = fixtures.MockHttpLayer

        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "http://sword/1")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        with self.assertRaises(deposit.DepositException):   # because this is what the mock does if it gets called
            deposit.process_notification(acc, note, since)

    def test_13_malformed_config(self):
        # give us an account to process for
        acc = models.Account()
        acc.add_sword_credentials("acc1", "pass1", "/id/config")
        acc.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc.save()

        # create a notification
        source = fixtures.NotificationFactory.outgoing_notification()
        note = jmod.OutgoingNotification(source)

        # get a since date, doesn't really matter what it is
        since = dates.now()

        with self.assertRaises(deposit.DepositException):   # because this is what the mock does if it gets called
            deposit.process_notification(acc, note, since)