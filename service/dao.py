"""
This module contains all the Data Access Objects for models which are persisted to Elasticsearch
at some point in their lifecycle.

Each DAO is an extension of the octopus ESDAO utility class which provides all of the ES-level heavy lifting,
so these DAOs mostly just provide information on where to persist the data, and some additional storage-layer
query methods as required
"""

from octopus.modules.es import dao

class RepositoryStatusDAO(dao.ESDAO):
    """
    DAO for RepositoryStatus
    """
    __type__ = "sword_repository_status"

class DepositRecordDAO(dao.ESDAO):
    """
    DAO for DepositRecord
    """
    __type__ = "sword_deposit_record"

    @classmethod
    def pull_by_ids(cls, notification_id, repository_id):
        """
        Get exactly one deposit record back associated with the notification_id and the repository_id

        :param notification_id:
        :param repository_id:
        :return:
        """
        q = DepositRecordQuery(notification_id, repository_id)
        obs = cls.object_query(q=q.query())
        if len(obs) > 0:
            return obs[0]

class DepositRecordQuery(object):
    """
    Query generator for retrieving deposit records by notification id and repository id
    """
    def __init__(self, notification_id, repository_id):
        self.notification_id = notification_id
        self.repository_id = repository_id

    def query(self):
        """
        Return the query as a python dict suitable for json serialisation

        :return: elasticsearch query
        """
        return {
            "query" : {
                "bool" : {
                    "must" : [
                        # {"term" : {"repository.exact" : self.repository_id}},
                        # 2018-03-07 TD : as of fix 2016-08-26 in models/sword.py
                        #                 this has to match 'repo.exact' instead!
                        #                 What a bug, good grief!
                        {"term" : {"repo.exact" : self.repository_id}},
                        {"term" : {"notification.exact" : self.notification_id}}
                    ]
                }
            },
            "sort" : {"last_updated" : {"order" : "desc"}}
        }

class AccountDAO(dao.ESDAO):
    """
    DAO for Account
    """
    __type__ = "account"

    @classmethod
    def with_sword_activated(cls):
        """
        List all accounts in JPER that have sword deposit activated

        :return: list of sword enabled accounts
        """
        q = SwordAccountQuery()
        all = []
        for acc in cls.scroll(q=q.query()):
            # we need to do this because of the scroll keep-alive
            all.append(acc)
        return all

class SwordAccountQuery(object):
    """
    Query generator for accounts which have sword activated
    """
    def __init__(self):
        pass

    def query(self):
        """
        Return the query as a python dict suitable for json serialisation

        :return: elasticsearch query
        """
        return {
            "query" : {
                "query_string" : {
                    "query" : "_exists_:sword.collection AND sword.collection:/.+/"
                }
            }
        }

class RepositoryDepositLogDAO(dao.ESDAO):
    """
    DAO for RepositoryDepositLog
    """
    __type__ = "sword_repository_deposit_log"

    @classmethod
    def pull_by_id(cls, repository_id):
        """
        Get exactly one deposit record back associated with the notification_id and the repository_id

        :param notification_id:
        :param repository_id:
        :return:
        """
        q = RepositoryDepositLogQuery(repository_id)
        obs = cls.object_query(q=q.query())
        if len(obs) > 0:
            return obs[0]

class RepositoryDepositLogQuery(object):
    """
    Query generator for retrieving deposit records by notification id and repository id
    """
    def __init__(self, repository_id):
        self.repository_id = repository_id

    def query(self):
        """
        Return the query as a python dict suitable for json serialisation

        :return: elasticsearch query
        """
        return {
            "query" : {
                "bool" : {
                    "must" : {
                        "term": {"repo.exact" : self.repository_id}
                    }
                }
            },
            "sort" : {"last_updated" : {"order" : "desc"}},
            "size": 1
        }
