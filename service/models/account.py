"""
Model objects used to represent data from the JPER account system
"""

from flask_login import UserMixin

from service import dao
from octopus.lib import dataobj

class Account(dataobj.DataObj, dao.AccountDAO, UserMixin):
    """
    Account model which mirrors the JPER account model, providing only the functions
    we need within the sword depositor
    """

    @property
    def api_key(self):
        """
        Get the API key for this account

        :return: the account's api key
        """
        return self._get_single("api_key", coerce=self._utf8_unicode())

    @property
    def packaging(self):
        """
        Get the list of supported packaging formats for this account

        :return: list of packaging formats
        """
        return self._get_list("packaging", coerce=self._utf8_unicode())

    def add_packaging(self, val):
        """
        Add a packaging format to the list of supported formats

        :param val: format identifier
        :return:
        """
        self._add_to_list("packaging", val, coerce=self._utf8_unicode(), unique=True)

    def add_sword_credentials(self, username, password, collection):
        """
        Add the sword credentials for the user

        :param username: username to deposit to repository as
        :param password: password of repository user account
        :param collection: collection url to deposit to
        :return:
        """
        self._set_single("sword.username", username, coerce=self._utf8_unicode())
        self._set_single("sword.password", password, coerce=self._utf8_unicode())
        self._set_single("sword.collection", collection, coerce=self._utf8_unicode())

    @property
    def sword_collection(self):
        """
        Get the url of the collection in the repository to deposit to

        :return: collection url
        """
        return self._get_single("sword.collection", coerce=self._utf8_unicode())

    @property
    def sword_username(self):
        """
        Get the username of the repository account to deposit as

        :return: username
        """
        return self._get_single("sword.username", coerce=self._utf8_unicode())

    @property
    def sword_password(self):
        """
        Get the password for the repository user to deposit as

        :return: password
        """
        return self._get_single("sword.password", coerce=self._utf8_unicode())

    @property
    def repository_software(self):
        """
        Get the name of the repository software we are depositing to

        :return: software name (e.g. eprints, dspace)
        """
        return self._get_single("repository.software", coerce=self._utf8_unicode())

    @repository_software.setter
    def repository_software(self, val):
        """
        Set the name of the repository software we are depositing to

        :param val: software name
        :return:
        """
        self._set_single("repository.software", val, coerce=self._utf8_unicode())
