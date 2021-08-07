"""
Fixtures for testing sword features
"""

from copy import deepcopy

class SwordFactory(object):
    """
    Class which provides access to the various fixtures used for testing the sword features
    """
    @classmethod
    def repository_status(cls):
        """
        Example repository status

        :return:
        """
        return deepcopy(REPOSITORY_STATUS)

    @classmethod
    def repository_status_do_test(cls):
        """
        Another example repository status

        :return:
        """
        return deepcopy(REPOSITORY_STATUS_DO)

    @classmethod
    def deposit_record(cls):
        """
        Example deposit record

        :return:
        """
        return deepcopy(DEPOSIT_RECORD)

    @classmethod
    def deposit_record_do_test(cls):
        """
        Another example deposit record

        :return:
        """
        return deepcopy(DEPOSIT_RECORD)

REPOSITORY_STATUS_DO = {
    "id" : "12345",
    "created_date" : "1970-01-01T00:00:00Z",
    "last_updated" : "1971-01-01T00:00:00Z",
    "last_deposit_date" : ("1972-01-01", "1972-01-01T00:00:00Z"),
    "status" : "succeeding",
    "last_tried" : "1971-01-01T00:00:00Z",
    "retries" : 14
}
"""Example repository status"""

REPOSITORY_STATUS = {
    "id" : "12345",
    "last_updated" : "1970-01-01T00:00:00Z",
    "created_date" : "1971-01-01T00:00:00Z",

    "last_deposit_date" : "1972-01-01",
    "status" : "succeeding",
    "retries" : 14,
    "last_tried" : "1971-01-01T00:00:00Z"
}
"""Another example repository status"""

DEPOSIT_RECORD_DO = {
    "id" : "12345",
    "created_date" : "1970-01-01T00:00:00Z",
    "last_updated" : "1971-01-01T00:00:00Z",
    "repository" : "12345",
    "deposit_date" : "1972-01-01T00:00:00Z",
    "metadata_status" : "deposited",
    "content_status" : "none",
    "completed_status" : "none"
}
"""Example deposit record"""

DEPOSIT_RECORD = {
    "id" : "12345",
    "last_updated" : "1970-01-01T00:00:00Z",
    "created_date" : "1971-01-01T00:00:00Z",

    #"repository" : "12345",
    "notification" : "abcde",
    "deposit_date" : "1972-01-01T00:00:00Z",
    "metadata_status" : "deposited",
    "content_status" : "none",
    "completed_status" : "none"
}
"""Another example deposit record"""