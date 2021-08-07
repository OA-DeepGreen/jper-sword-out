"""
Module which controls the active status of depositing accounts
"""
from service import models


def activate_deposit(acc_id):
    """
    Activate the repository's deposit process.

    This sets the repository status to "succeeding", which in turn means the processor will
    pick up this account and run deposits against the repo.

    :param acc_id: account to activate
    :return:
    """
    # see if there's a repository status for this account
    rs = models.RepositoryStatus.pull(acc_id)

    # if not make one
    if rs is None:
        rs = models.RepositoryStatus()
        rs.id = acc_id
        rs.status = "succeeding"
        rs.save()
        return

    # if there is, reset it ready to go again
    rs.activate()
    rs.save()

def deactivate_deposit(acc_id):
    """
    Deactivate the repository's deposit process

    This sets the repository status to "failing", which in turn means the processor will ignore this
    account in its normal run

    :param acc_id: account to deactivate
    :return:
    """
    # see if there's a repository status for this account
    rs = models.RepositoryStatus.pull(acc_id)

    # if not, that's as good as being deactivated
    if rs is None:
        return

    # if there is, deactivate it
    rs.deactivate()
    rs.save()