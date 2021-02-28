"""
Tests on the JPER client
"""

# from octopus.modules.es.testindex import ESTestCase
from unittest import TestCase
from standalone_octopus.lib import http
from standalone_octopus.modules.jper import client, models
from service.tests import fixtures
import urllib.parse, json
from io import StringIO

def mock_list(url, *args, **kwargs):
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    if params["since"][0] == "1970-01-01T00:00:00Z":
        nl = fixtures.NotificationFactory.notification_list(params["since"][0], pageSize=2, count=2)
        return http.MockResponse(200, json.dumps(nl))
    elif params["since"][0] == "1971-01-01T00:00:00Z":
        before = (int(params["page"][0]) - 1) * int(params["pageSize"][0])
        nl = fixtures.NotificationFactory.notification_list(params["since"][0], page=int(params["page"][0]), pageSize=int(params["pageSize"][0]), count=before + 3)
        return http.MockResponse(200, json.dumps(nl))
    elif params["since"][0] == "1972-01-01T00:00:00Z":
        return None
    elif params["since"][0] == "1973-01-01T00:00:00Z":
        return http.MockResponse(401)
    elif params["since"][0] == "1974-01-01T00:00:00Z":
        err = fixtures.NotificationFactory.error_response()
        return http.MockResponse(400, json.dumps(err))

def mock_get_content(url, *args, **kwargs):
    parsed = urllib.parse.urlparse(url)

    if parsed.path.endswith("/content"):
        return http.MockResponse(200, "default content"), "", 0
    elif parsed.path.endswith("/content/SimpleZip"):
        return http.MockResponse(200, "simplezip"), "", 0
    elif parsed.path.endswith("nohttp"):
        return None, "", 0
    elif parsed.path.endswith("auth"):
        return http.MockResponse(401), "", 0
    elif parsed.path.endswith("error"):
        err = fixtures.NotificationFactory.error_response()
        return http.MockResponse(400, json.dumps(err)), "", 0

def mock_iterate(url, *args, **kwargs):
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    if params["page"][0] == "1":
        nl = fixtures.NotificationFactory.notification_list(params["since"][0], page=int(params["page"][0]), pageSize=2, count=4, ids=["1111", "2222"])
        return http.MockResponse(200, json.dumps(nl))
    elif params["page"][0] == "2":
        nl = fixtures.NotificationFactory.notification_list(params["since"][0], page=int(params["page"][0]), pageSize=2, count=4, ids=["3333", "4444"])
        return http.MockResponse(200, json.dumps(nl))
    raise Exception()

API_KEY = "testing"
JPER_BASE_URL = "http://localhost:5024"

class TestModels(TestCase):
    def setUp(self):
        super(TestModels, self).setUp()

        self.old_http_get = http.get
        self.old_http_get_stream = http.get_stream

    def tearDown(self):
        super(TestModels, self).tearDown()

        http.get = self.old_http_get
        http.get_stream = self.old_http_get_stream

    def test_01_list_notifications(self):
        # specify the mock for the http.get function
        http.get = mock_list

        # create a client we can use
        c = client.JPER(api_key=API_KEY, base_url=JPER_BASE_URL)

        # first try with just a since date
        notes = c.list_notifications("1970-01-01")
        assert len(notes.notifications) == 2
        assert notes.since == "1970-01-01T00:00:00Z"

        # now try with all the other parameters
        notes = c.list_notifications("1971-01-01T00:00:00Z", page=5, page_size=100, repository_id="12345")
        assert notes.since == "1971-01-01T00:00:00Z"
        assert notes.page == 5
        assert notes.page_size == 100
        assert len(notes.notifications) == 3

        # check a failed http request
        with self.assertRaises(client.JPERConnectionException):
            notes = c.list_notifications("1972-01-01")

        # failed auth
        with self.assertRaises(client.JPERAuthException):
            notes = c.list_notifications("1973-01-01")

        # an error
        with self.assertRaises(client.JPERException):
            notes = c.list_notifications("1974-01-01", page="forty")

    def test_02_get_content(self):
        # specify the mock for the http.get function
        http.get_stream = mock_get_content

        # create a client we can use
        c = client.JPER(api_key=API_KEY, base_url=JPER_BASE_URL)

        # try the default content url
        url = "http://localhost:5024/notification/12345/content"
        gen, headers = c.get_content(url)
        assert hasattr(gen, "next")
        assert next(gen) == "default content"

        # try a specific content url
        url = "http://localhost:5024/notification/12345/content/SimpleZip"
        gen, headers = c.get_content(url)
        assert hasattr(gen, "next")
        assert next(gen) == "simplezip"

        # check a failed http request
        with self.assertRaises(client.JPERConnectionException):
            notes = c.get_content("/nohttp")

        # failed auth
        with self.assertRaises(client.JPERAuthException):
            notes = c.get_content("/auth")

        # an error
        with self.assertRaises(client.JPERException):
            notes = c.get_content("/error")

    def test_03_iterate_notifications(self):
        # specify the mock for the http.get function
        http.get = mock_iterate

        # create a client we can use
        c = client.JPER(api_key=API_KEY, base_url=JPER_BASE_URL)

        ids = []
        for note in c.iterate_notifications("1970-01-01T00:00:00Z", repository_id="askdjfhas", page_size=2):
            assert isinstance(note, models.OutgoingNotification)
            ids.append(note.id)
        assert ids == ["1111", "2222", "3333", "4444"]

    def test_04_notification_package_link(self):
        source = fixtures.NotificationFactory.outgoing_notification()
        note = models.OutgoingNotification(source)

        # try getting the two link types we know are in the notification
        faj = note.get_package_link("https://pubrouter.jisc.ac.uk/FilesAndJATS")
        assert faj is not None
        assert faj.get("url") == "http://router.jisc.ac.uk/api/v1/notification/1234567890/content"

        sz = note.get_package_link("http://purl.org/net/sword/package/SimpleZip")
        assert sz is not None
        assert sz.get("url") == "http://router.jisc.ac.uk/api/v1/notification/1234567890/content/SimpleZip"

        # try getting a link which doesn't exist
        nx = note.get_package_link("http://some.package/or/other")
        assert nx is None