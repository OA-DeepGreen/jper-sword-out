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
    def email(self):
        """
        Get the email for this account

        :return: the account's email
        """
        return self._get_single("email", coerce=self._utf8_unicode())

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

    @property
    def sword_collection(self):
        return self._get_single("sword.collection", coerce=self._utf8_unicode())

    @sword_collection.setter
    def sword_collection(self, val):
        self._set_single("sword.collection", val, coerce=self._utf8_unicode())

    @property
    def sword_username(self):
        return self._get_single("sword.username", coerce=self._utf8_unicode())

    @sword_username.setter
    def sword_username(self, val):
        self._set_single("sword.username", val, coerce=self._utf8_unicode())

    @property
    def sword_password(self):
        return self._get_single("sword.password", coerce=self._utf8_unicode())

    @sword_password.setter
    def sword_password(self, val):
        self._set_single("sword.password", val, coerce=self._utf8_unicode())

    @property
    def sword_deposit_method(self):
        return self._get_single("sword.deposit_method", coerce=self._utf8_unicode())

    @sword_deposit_method.setter
    def sword_deposit_method(self, val):
        if val.strip().lower() not in ["single zip file", "individual files"]:
            raise dataobj.DataSchemaException("Sword deposit method must only contain " +
                                              "'single zip file' or 'individual files'")
        self._set_single("sword.deposit_method", val.strip().lower(), coerce=self._utf8_unicode())

    def add_sword_credentials(self, username, password, collection, deposit_method):
        """
        Add the sword credentials for the user

        :param username: username to deposit to repository as
        :param password: password of repository user account
        :param collection: collection url to deposit to
        :param deposit_method: the method used to make a deposit
        :return:
        """
        self.sword_username = username
        self.sword_password = password
        self.sword_collection = collection
        self.sword_deposit_method = deposit_method

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
