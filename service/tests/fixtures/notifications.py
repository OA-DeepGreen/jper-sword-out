"""
Fixtures for testing notifications
"""

from copy import deepcopy
from standalone_octopus.lib import dates, paths
import os

RESOURCES = paths.rel2abs(__file__, "..", "resources")
"""Path to the test resources directory, calculated relative to this file"""

class NotificationFactory(object):
    """
    Class which provides access to the various fixtures used for testing the notifications
    """

    @classmethod
    def notification_list(cls, since, page=1, pageSize=10, count=1, ids=None, analysis_dates=None):
        """
        Example notification list

        :param since: since date for list
        :param page: page number of list
        :param pageSize: number of results in list
        :param count: total number of results
        :param ids: ids of notifications to be included
        :param analysis_dates: analysis dates of notifications; should be same length as ids, as they will be tied up
        :return:
        """
        nl = deepcopy(NOTIFICATION_LIST)
        nl["since"] = since
        nl["page"] = page
        nl["pageSize"] = pageSize
        nl["total"]= count
        nl["timestamp"] = dates.now()

        this_page = pageSize if page * pageSize <= count else count - ((page - 1) * pageSize)
        for i in range(this_page):
            note = deepcopy(OUTGOING)
            if ids is not None:
                note["id"] = ids[i]
            if analysis_dates is not None:
                note["analysis_date"] = analysis_dates[i]
            nl["notifications"].append(note)
        return nl

    @classmethod
    def error_response(cls):
        """
        JPER API error response

        :return: error response
        """
        return deepcopy(LIST_ERROR)

    @classmethod
    def unrouted_notification(cls):
        """
        Example unrouted notification

        :return:
        """
        return deepcopy(BASE_NOTIFICATION)

    @classmethod
    def outgoing_notification(cls):
        """
        Example outgoing notification

        :return:
        """
        return deepcopy(OUTGOING)

    @classmethod
    def special_character_notification(cls):
        """
        Example special character notification

        :return:
        """
        return deepcopy(SPECIAL_CHARACTER)

    @classmethod
    def example_package_path(cls):
        """
        Path to binary file which can be used for testing

        :return:
        """
        return os.path.join(RESOURCES, "example.zip")

LIST_ERROR = {
    "error" : "request failed"
}
"""Example API error"""

BASE_NOTIFICATION = {
    "id" : "1234567890",
    "created_date" : "2015-02-02T00:00:00Z",

    "event" : "publication",

    "provider" : {
        "id" : "pub1",
        "agent" : "test/0.1",
        "ref" : "xyz",
        "route" : "api"
    },

    "content" : {
        "packaging_format" : "https://pubrouter.jisc.ac.uk/FilesAndJATS",
        "store_id" : "abc"
    },

    "links" : [
        {
            "type" : "splash",
            "format" : "text/html",
            "access" : "public",
            "url" : "http://example.com/article/1"
        },
        {
            "type" : "fulltext",
            "format" : "application/pdf",
            "access" : "public",
            "url" : "http://example.com/article/1/pdf"
        }
    ],

    "embargo" : {
        "end" : "2016-01-01T00:00:00Z",
        "start" : "2015-01-01T00:00:00Z",
        "duration" : 12
    },

    "metadata" : {
        "title" : "Test Article",
        "version" : "AAM",
        "publisher" : "Premier Publisher",
        "source" : {
            "name" : "Journal of Important Things",
            "identifier" : [
                {"type" : "issn", "id" : "1234-5678" },
                {"type" : "eissn", "id" : "1234-5678" },
                {"type" : "pissn", "id" : "9876-5432" },
                {"type" : "doi", "id" : "10.pp/jit" }
            ]
        },
        "identifier" : [
            {"type" : "doi", "id" : "10.pp/jit.1" }
        ],
        "type" : "article",
        "author" : [
            {
                "name" : "Richard Jones",
                "identifier" : [
                    {"type" : "orcid", "id" : "aaaa-0000-1111-bbbb"},
                    {"type" : "email", "id" : "richard@example.com"},
                ],
                "affiliation" : "Cottage Labs, HP3 9AA"
            },
            {
                "name" : "Mark MacGillivray",
                "identifier" : [
                    {"type" : "orcid", "id" : "dddd-2222-3333-cccc"},
                    {"type" : "email", "id" : "mark@example.com"},
                ],
                "affiliation" : "Cottage Labs, EH9 5TP"
            }
        ],
        "language" : "eng",
        "publication_date" : "2015-01-01T00:00:00Z",
        "date_accepted" : "2014-09-01T00:00:00Z",
        "date_submitted" : "2014-07-03T00:00:00Z",
        "license_ref" : {
            "title" : "CC BY",
            "type" : "CC BY",
            "url" : "http://creativecommons.org/cc-by",
            "version" : "4.0",
        },
        "project" : [
            {
                "name" : "BBSRC",
                "identifier" : [
                    {"type" : "ringold", "id" : "bbsrcid"}
                ],
                "grant_number" : "BB/34/juwef"
            }
        ],
        "subject" : ["science", "technology", "arts", "medicine"]
    }
}
"""Example base notification"""

NOTIFICATION_LIST = {
    "since" : None,
    "page" : None,
    "pageSize" : None,
    "timestamp" : None,
    "total" : 1,
    "notifications" : []
}
"""structure for notification list"""

OUTGOING = {

    "id" : "1234567890",
    "created_date" : "2015-02-02T00:00:00Z",
    "analysis_date" : "2015-02-02T00:00:00Z",

    "event" : "submission",

    "content" : {
        "packaging_format" : "https://pubrouter.jisc.ac.uk/FilesAndJATS",
    },

    "links" : [
        {
            "type" : "splash",
            "format" : "text/html",
            "url" : "http://router.jisc.ac.uk/api/v1/notification/1234567890/content/1"
        },
        {
            "type" : "fulltext",
            "format" : "application/pdf",
            "url" : "http://router.jisc.ac.uk/api/v1/notification/1234567890/content/2"
        },
        {
            "type" : "package",
            "format" : "application/zip",
            "url" : "http://router.jisc.ac.uk/api/v1/notification/1234567890/content/SimpleZip",
            "packaging" : "http://purl.org/net/sword/package/SimpleZip"
        },
        {
            "type" : "package",
            "format" : "application/zip",
            "url" : "http://router.jisc.ac.uk/api/v1/notification/1234567890/content",
            "packaging" : "https://pubrouter.jisc.ac.uk/FilesAndJATS"
        }
    ],

    "embargo" : {
        "end" : "2016-01-01T00:00:00Z",
        "start" : "2015-01-01T00:00:00Z",
        "duration" : 12
    },

    "metadata" : {
        "title" : "Test Article",
        "version" : "AAM",
        "publisher" : "Premier Publisher",
        "source" : {
            "name" : "Journal of Important Things",
            "identifier" : [
                {"type" : "issn", "id" : "1234-5678" },
                {"type" : "eissn", "id" : "1234-5678" },
                {"type" : "pissn", "id" : "9876-5432" },
                {"type" : "doi", "id" : "10.pp/jit" }
            ]
        },
        "identifier" : [
            {"type" : "doi", "id" : "10.pp/jit.1" }
        ],
        "type" : "article",
        "author" : [
            {
                "name" : "Richard Jones",
                "identifier" : [
                    {"type" : "orcid", "id" : "aaaa-0000-1111-bbbb"},
                    {"type" : "email", "id" : "richard@example.com"},
                ],
                "affiliation" : "Cottage Labs"
            },
            {
                "name" : "Mark MacGillivray",
                "identifier" : [
                    {"type" : "orcid", "id" : "dddd-2222-3333-cccc"},
                    {"type" : "email", "id" : "mark@example.com"},
                ],
                "affiliation" : "Cottage Labs"
            }
        ],
        "language" : "eng",
        "publication_date" : "2015-01-01T00:00:00Z",
        "date_accepted" : "2014-09-01T00:00:00Z",
        "date_submitted" : "2014-07-03T00:00:00Z",
        "license_ref" : {
            "title" : "CC BY",
            "type" : "CC BY",
            "url" : "http://creativecommons.org/cc-by",
            "version" : "4.0",
        },
        "project" : [
            {
                "name" : "BBSRC",
                "identifier" : [
                    {"type" : "ringold", "id" : "bbsrcid"}
                ],
                "grant_number" : "BB/34/juwef"
            }
        ],
        "subject" : ["science", "technology", "arts", "medicine"]
    }
}
"""example outgoing notification"""

SPECIAL_CHARACTER = {
        "embargo": {
                "duration": 0
        },
        "links": [{
                "url": "https://pubrouter.jisc.ac.uk/api/v1/notification/4e8f4bef41254539a28e072c1e85d9a2/proxy/d0ec9aa8125f4e81aede7dfeaa5bc9e2",
                "type": "fulltext",
                "format": "text/html"
        }],
        "analysis_date": "2016-02-23T22:41:47Z",
        "event": "acceptance",
        "created_date": "2016-02-23T22:35:46Z",
        "id": "4e8f4bef41254539a28e072c1e85d9a2",
        "metadata": {
                "language": "eng",
                "title": "Relationship between maxillary central incisor proportions and\\u00a0facial proportions.".decode("unicode_escape"),
                "author": [{
                        "affiliation": "Senior Specialty Registrar, Orthodontics, Guy's Hospital, London, UK.",
                        "identifier": [{
                                "type": "ORCID",
                                "id": "0000-0003-2731-183X"
                        }],
                        "name": "Radia S"
                },
                {
                        "affiliation": "Professor, Biostatistics, University of Bristol, Bristol, UK.",
                        "name": "Sherriff M"
                },
                {
                        "affiliation": "Professor and Head, Department of Orthodontics, King's College University, London, UK.",
                        "name": "McDonald F"
                },
                {
                        "affiliation": "Consultant Orthodontist, Kingston and St George's Hospitals and Medical School, London, UK. Electronic address: farhad.naini@yahoo.co.uk.",
                        "name": "Naini FB"
                }],
                "source": {
                        "identifier": [{
                                "type": "issn",
                                "id": "0022-3913"
                        },
                        {
                                "type": "eissn",
                                "id": "1097-6841"
                        }],
                        "name": "The Journal of prosthetic dentistry"
                },
                "publication_date": "2016-01-12T00:00:00Z",
                "identifier": [{
                        "type": "10.1016/j.prosdent.2015.10.019",
                        "id": "doi"
                },
                {
                        "type": "26794701",
                        "id": "pmid"
                }],
                "type": "Journal Article"
        }
}
