"""
Test the full range of deposit features against a test repository

DO NOT RUN THIS TEST AS-IS

In order to successfully run this test you need a repository set up to receive the deposits via SWORDv2, and
you need to tell this class the parameters of the deposit.

For example, if depositing against a Simple Sword Server test instance, you could use something like

::

    COL = "http://localhost:8080/col-uri/dbc32f11-3ffa-4fdd-88bc-af4544fa97d9"
    ERR_COL = "http://localhost:8080/col-uri/thisdoesntexist"
    UN = "sword"
    PW = "sword"
    REPO_SOFTWARE = "SSS"
    PACKAGING = "http://purl.org/net/sword/package/SimpleZip"

Here, the only thing you would need to customise is the COL, to point to a collection which actually
exists in SSS.

"""
from octopus.modules.es.testindex import ESTestCase
from service import deposit, models
from service.tests import fixtures
from octopus.modules.jper import models as jper
from octopus.modules.store import store
from octopus.core import app
from lxml import etree
import urllib.parse, json, time
from octopus.lib import http, dates, paths

# NOTE: you need to be running a SWORD server for these tests to operate.
# Recommend just starting an instance of SSS, then picking a collection
# and sticking it here:

"""
Local EPrints Configuration


COL = "http://eprints.ooz.cottagelabs.com/id/contents"
ERR_COL = "http://eprints.ooz.cottagelabs.com/id/thisdoesntexist"
UN = "admin"
PW = "admin"
REPO_SOFTWARE = "eprints"

PACKAGING = "http://purl.org/net/sword/package/SimpleZip"
"""

"""
SSS Configuration
"""

#COL = "http://localhost:8080/col-uri/dbc32f11-3ffa-4fdd-88bc-af4544fa97d9"
COL = "http://localhost:8080/col-uri/1c1099ef-4500-4ebd-805f-23fdbfb5165b"
ERR_COL = "http://localhost:8080/col-uri/thisdoesntexist"
UN = "sword"
PW = "sword"
REPO_SOFTWARE = "SSS"

PACKAGING = "http://purl.org/net/sword/package/SimpleZip"

"""
Remote EPrints Configuration

COL = "http://eprints2.cottagelabs.com/id/contents"
ERR_COL = "http://eprints2.cottagelabs.com/id/thisdoesntexist"
UN = "huddersfield"
PW = "password"
REPO_SOFTWARE = "eprints"

PACKAGING = "http://purl.org/net/sword/package/SimpleZip"
"""

def mock_get_content(url, *args, **kwargs):
    with open(fixtures.NotificationFactory.example_package_path()) as f:
        cont = f.read()
    return http.MockResponse(200, cont), "", 0

class TestDeposit(ESTestCase):
    def setUp(self):
        super(TestDeposit, self).setUp()

        self.old_http_get = http.get
        self.old_http_get_stream = http.get_stream

        self.stored = []

        self.store_impl = app.config.get("STORE_IMPL")
        app.config["STORE_IMPL"] = "octopus.modules.store.store.TempStore"

        self.store_responses = app.config.get("STORE_RESPONSE_DATA")
        app.config["STORE_RESPONSE_DATA"] = True

    def tearDown(self):
        http.get = self.old_http_get
        http.get_stream = self.old_http_get_stream

        sm = store.StoreFactory.get()
        for s in self.stored:
            sm.delete(s)

        tmp = store.StoreFactory.tmp()
        dirs = paths.list_subdirs(tmp.dir)
        for d in dirs:
            tmp.delete(d)

        app.config["STORE_IMPL"] = self.store_impl
        app.config["STORE_RESPONSE_DATA"] = self.store_responses

        super(TestDeposit, self).tearDown()

    def test_01_metadata_deposit_success(self):
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=True)

        assert receipt is not None
        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 2
        assert "metadata_deposit_response.xml" in files
        assert "metadata_deposit.txt" in files
        f = sm.get(deposit_record.id, "metadata_deposit_response.xml")
        xml = etree.parse(f)
        assert xml is not None

    def test_02_metadata_deposit_fail(self):
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, ERR_COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        with self.assertRaises(deposit.DepositException):
            deposit.metadata_deposit(note, acc, deposit_record, complete=True)

        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "failed"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 1
        assert "metadata_deposit.txt" in files

    def test_03_content_deposit_success(self):
        # first do a successful metadata deposit
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=False)

        path = fixtures.NotificationFactory.example_package_path()
        with open(path, 'rb') as f:
            deposit.package_deposit(receipt, f, PACKAGING, acc, deposit_record)

        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"
        assert deposit_record.content_status == "deposited"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 3
        assert "metadata_deposit.txt" in files
        assert "content_deposit.txt" in files

    def test_04_content_deposit_fail(self):
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        # first a successful deposit of metadata
        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=False)

        # now mess with the receipt to generate a failure
        em = receipt.edit_media
        bits = em.split("/")
        bits[len(bits) - 1] = "randomobjectidentifier"
        receipt.edit_media = "/".join(bits)

        path = fixtures.NotificationFactory.example_package_path()
        with open(path) as f:
            with self.assertRaises(deposit.DepositException):
                deposit.package_deposit(receipt, f, PACKAGING, acc, deposit_record)

        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"
        assert deposit_record.content_status == "failed"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 3
        assert "metadata_deposit.txt" in files
        assert "content_deposit.txt" in files

    def test_05_complete_deposit_success(self):
        # first do a successful metadata deposit
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=False)

        # now do a successful content deposit
        path = fixtures.NotificationFactory.example_package_path()
        with open(path) as f:
            deposit.package_deposit(receipt, f, PACKAGING, acc, deposit_record)

        # finally issue the complete request
        deposit.complete_deposit(receipt, acc, deposit_record)

        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"
        assert deposit_record.content_status == "deposited"
        if acc.repository_software == "eprints":
            assert deposit_record.completed_status == "none"
        else:
            assert deposit_record.completed_status == "deposited"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 4
        assert "metadata_deposit.txt" in files
        assert "content_deposit.txt" in files
        assert "complete_deposit.txt" in files

    def test_06_complete_deposit_fail(self):
        # first do a successful metadata deposit
        note = jper.OutgoingNotification(fixtures.NotificationFactory.outgoing_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=False)

        # now do a successful content deposit
        path = fixtures.NotificationFactory.example_package_path()
        with open(path) as f:
            deposit.package_deposit(receipt, f, PACKAGING, acc, deposit_record)

        # now mess with the receipt to generate a failure
        em = receipt.se_iri
        if em is None:  # EPrints doesn't return an SE-IRI
            em = receipt.edit
        bits = em.split("/")
        bits[len(bits) - 1] = "randomobjectidentifier"
        receipt.se_iri = "/".join(bits)

        # finally issue the complete request (if this is not an eprints repository)
        if acc.repository_software != "eprints":
            with self.assertRaises(deposit.DepositException):
                deposit.complete_deposit(receipt, acc, deposit_record)
        else:
            deposit.complete_deposit(receipt, acc, deposit_record)

        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"
        assert deposit_record.content_status == "deposited"
        if acc.repository_software == "eprints":
            assert deposit_record.completed_status == "none"
        else:
            assert deposit_record.completed_status == "failed"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 4
        assert "metadata_deposit.txt" in files
        assert "content_deposit.txt" in files
        assert "complete_deposit.txt" in files

    def test_07_full_cycle_success(self):
        # first load some accounts into the system, some with and some without sword support
        acc1 = models.Account()
        acc1.add_sword_credentials(UN, PW, COL)
        acc1.repository_software = REPO_SOFTWARE
        acc1.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc1.save()

        acc2 = models.Account()
        acc2.add_sword_credentials(UN, PW, COL)
        acc2.repository_software = REPO_SOFTWARE
        acc2.add_packaging("http://purl.org/net/sword/package/SimpleZip")
        acc2.save()

        acc3 = models.Account()
        acc3.save()

        acc4 = models.Account()
        acc4.save()

        # load a deposit status into the index for one of the accounts
        rs = models.RepositoryStatus()
        rs.id = acc1.id
        rs.last_deposit_date = dates.format(dates.before_now(3600))
        rs.status = "succeeding"
        rs.save()

        # make a (successful) deposit record for one of the notifications that we're going to get back
        dr = models.DepositRecord()
        dr.repository = acc1.id
        dr.notification = "1111"
        dr.metadata_status = "deposited"
        dr.content_status = "deposited"
        dr.completed_status = "deposited"
        dr.save(blocking=True)

        # pointer for the old http get method, which we may need to fall back to
        OLD_GET = self.old_http_get

        # some static dates that we want to use, and then check later
        acc1ld = dates.format(dates.before_now(1000))
        acc2ld = dates.format(dates.before_now(800))

        # now make some notifications to be returned over http
        # defining this mock here for convenience during development
        def mock_get_list_intercept(url, *args, **kwargs):
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)

            # if this is a request to list routed notifications we need to intercept and return the
            # mock response
            if "/routed/" in parsed.path:
                s = params["since"][0]
                p = int(params["page"][0])
                ps = int(params["pageSize"][0])

                # work out which account the request is for
                accid = parsed.path.split("/")[-1]
                if accid == acc1.id:
                    c = 5
                    ids = ["1111", "2222", "3333", "4444", "5555"]
                    ad = [
                        rs.last_deposit_date,
                        rs.last_deposit_date,
                        dates.format(dates.before_now(3000)),
                        dates.format(dates.before_now(2000)),
                        acc1ld
                    ]
                    nl = fixtures.NotificationFactory.notification_list(s, page=p, pageSize=ps, count=c, ids=ids, analysis_dates=ad)
                    return http.MockResponse(200, json.dumps(nl))
                elif accid == acc2.id:
                    c = 5
                    ids = ["4444", "5555", "6666", "7777", "8888"]
                    ad = [
                        dates.format(dates.before_now(3500)),
                        dates.format(dates.before_now(3500)),
                        dates.format(dates.before_now(3000)),
                        dates.format(dates.before_now(2000)),
                        acc2ld
                    ]
                    nl = fixtures.NotificationFactory.notification_list(s, page=p, pageSize=ps, count=c, ids=ids, analysis_dates=ad)
                    return http.MockResponse(200, json.dumps(nl))
                else:
                    # this means we've requested something for a non-sword enabled account
                    raise Exception()

            # otherwise this could be a request to the index or something, so we pass it on
            return OLD_GET(url *args, **kwargs)

        # set up the mocks on the http layer
        http.get = mock_get_list_intercept
        http.get_stream = mock_get_content

        # now run the full stack
        deposit.run(fail_on_error=True)

        # for some reason sometimes it takes a while for the index changes to be live, so whacking this up to
        # 5 seconds
        time.sleep(5)

        # now check over everything and make sure what we expected to happen happened

        # first that there are successful repository status records for both repositories
        rs1 = models.RepositoryStatus.pull(acc1.id)
        assert rs1.last_deposit_date == acc1ld
        assert rs1.status == "succeeding"
        assert rs1.retries == 0
        assert rs1.last_tried is None

        rs2 = models.RepositoryStatus.pull(acc2.id)
        assert rs2.last_deposit_date == acc2ld
        assert rs2.status == "succeeding"
        assert rs2.retries == 0
        assert rs2.last_tried is None

        # that there are deposit records for each notification in each account context
        ids = ["1111", "2222", "3333", "4444", "5555"]
        for id in ids:
            dr = models.DepositRecord.pull_by_ids(id, acc1.id)
            assert dr is not None
            assert dr.metadata_status == "deposited"
            assert dr.content_status == "deposited"
            assert dr.completed_status == "deposited"

        ids = ["4444", "5555", "6666", "7777", "8888"]
        for id in ids:
            dr = models.DepositRecord.pull_by_ids(id, acc2.id)
            assert dr is not None
            assert dr.metadata_status == "deposited"
            assert dr.content_status == "deposited"
            assert dr.completed_status == "deposited"

        # only 7 of the records (resulting in 9 deposit records) should actually have been deposited, because one of them already had a deposit record
        # check the tmp store to be sure
        tmp = store.StoreFactory.tmp()
        dirs = paths.list_subdirs(tmp.dir)
        assert len(dirs) == 9

        # each of those directories should be essentially the same, with the same 4 files in them
        for d in dirs:
            files = tmp.list(d)
            assert len(files) == 4
            assert "metadata_deposit.txt" in files
            assert "content_deposit.txt" in files
            assert "complete_deposit.txt" in files
            assert "metadata_deposit_response.xml" in files

    def test_08_metadata_deposit_success_special_character(self):
        note = jper.OutgoingNotification(fixtures.NotificationFactory.special_character_notification())

        acc = models.Account()
        acc.add_sword_credentials(UN, PW, COL)
        acc.repository_software = REPO_SOFTWARE

        deposit_record = models.DepositRecord()
        deposit_record.id = deposit_record.makeid()
        self.stored.append(deposit_record.id)

        receipt = deposit.metadata_deposit(note, acc, deposit_record, complete=True)

        assert receipt is not None
        # check the properties of the deposit_record
        assert deposit_record.metadata_status == "deposited"

        # check that a copy has been kept in the local store
        sm = store.StoreFactory.get()
        assert sm.exists(deposit_record.id)
        files = sm.list(deposit_record.id)
        assert len(files) == 2
        assert "metadata_deposit_response.xml" in files
        assert "metadata_deposit.txt" in files
        f = sm.get(deposit_record.id, "metadata_deposit_response.xml")
        xml = etree.parse(f)
        assert xml is not None
