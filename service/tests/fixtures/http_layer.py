from sword2 import HttpLayer, HttpResponse
from requests.auth import HTTPBasicAuth

class MockHttpResponse(HttpResponse):
    def __init__(self, *args, **kwargs):
        self.resp = None
        if len(args) > 0:
            self.resp = args[0]

    def __getitem__(self, att):
        if att == "status":
            return 201
        return None

    def __repr__(self):
        return self.resp.__repr__()

    def __dict__(self):
        return {}

    @property
    def status(self):
        return 201

    def get(self, att, default=None):
        if att == "status":
            return 201
        return default

    def keys(self):
        return {}

class MockHttpLayer(HttpLayer):
    def __init__(self, *args, **kwargs):
        self.username = None
        self.password = None
        self.auth = None

    def add_credentials(self, username, password):
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)

    def request(self, uri, method, headers=None, payload=None):    # Note that body can be file-like
        return MockHttpResponse(), ""

