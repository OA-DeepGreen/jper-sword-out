from service import models
from octopus.modules.jper import client
from octopus.core import app
from octopus.lib import dates
import os

def debug_run():
    """
    Execute a single pass on all the accounts that have sword activated and process all
    of their notifications since the last time their account was synchronised, until now.
    This is written out into a log for debug purposes.
    """
    today = dates.datetime.today().strftime('%Y-%m-%d')
    path = os.path.join("logs", today)
    os.makedirs(path, exist_ok=True)
    fname = os.path.join(path, "debug_deposit.csv")
    with open(fname, "a") as f:
        f.write(f"Account id, status, try_deposit, since, safe_since, number_of_notifications, number_to_deposit\n")
    # list all the accounts that have sword activated
    accs = models.Account.with_sword_activated()
    delay = app.config.get("LONG_CYCLE_RETRY_DELAY")
    delta_days = app.config.get("DEFAULT_SINCE_DELTA_DAYS")
    # process each account
    for acc in accs:
        j = client.JPER(api_key=acc.api_key)
        fname2 = os.path.join(path, f"{acc.id}.csv")
        with open(fname2, "a") as f2:
            f2.write(f"note_id,doi,date_created,has_deposit_record,dr_id,will_deposit\n")
        repository_status = models.RepositoryStatus.pull(acc.id)
        status = "new - succeeding"
        since = app.config.get("DEFAULT_SINCE_DATE")
        try_deposit = True
        if repository_status:
            status = repository_status.status
            since = repository_status.last_deposit_date
            if repository_status.status == "failing":
                try_deposit = False
            if repository_status.status == "problem" and not repository_status.can_retry(delay):
                try_deposit = False
        safe_since = dates.format(dates.parse(since) - dates.timedelta(days=delta_days))
        number_of_notifications = 0
        number_to_deposit = 0
        if try_deposit:
            for note in j.iterate_notifications(safe_since, repository_id=acc.id):
                date_created = note.data["created_date"]
                doi = _get_note_doi(note)
                has_deposit_record = False
                will_deposit = True
                dr_id = ""
                number_of_notifications += 1
                dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
                if dr:
                    has_deposit_record = True
                    dr_id = dr.id
                    # was this a successful deposit?  if so, don't re-run
                    if dr.was_successful():
                        will_deposit = False
                    else:
                        drs = models.DepositRecord.pull_all_by_ids(note.id, acc.id)
                        if len(drs) >= app.config.get("MAX_DEPOSIT_ATTEMPTS", 10):
                            print("Notification:{y} for Account:{x} has been attempted {z} times - skipping".format(
                                x=acc.id,
                                y=note.id,
                                z=len(drs)))
                            will_deposit = False
                    if dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge":
                        will_deposit = False
                if will_deposit:
                    number_to_deposit += 1
                with open(fname2, "a") as f2:
                    f2.write(f"{note.id},{doi},{date_created},{has_deposit_record},{dr_id},{will_deposit}\n")
        with open(fname, "a") as f:
            f.write(f"{acc.id}, {status}, {try_deposit}, {since}, {safe_since}, {number_of_notifications}, {number_to_deposit}\n")

def debug_run_for_account(account_id):
    """
    Execute a single pass for the account and process all
    of their notifications since the last time their account was synchronised, until now.
    This is written out into a log for debug purposes.
    """
    acc = models.Account.pull(account_id)
    today = dates.datetime.today().strftime('%Y-%m-%d')
    path = os.path.join("logs", today)
    os.makedirs(path, exist_ok=True)
    delta_days = app.config.get("DEFAULT_SINCE_DELTA_DAYS")
    # process the account
    j = client.JPER(api_key=acc.api_key)
    fname2 = os.path.join(path, f"{acc.id}.csv")
    with open(fname2, "a") as f2:
        f2.write(f"note_id,doi,date_created,has_deposit_record,dr_id,will_deposit\n")
    repository_status = models.RepositoryStatus.pull(acc.id)
    since = app.config.get("DEFAULT_SINCE_DATE")
    if repository_status:
        since = repository_status.last_deposit_date
    safe_since = dates.format(dates.parse(since) - dates.timedelta(days=delta_days))
    number_of_notifications = 0
    number_to_deposit = 0
    for note in j.iterate_notifications(safe_since, repository_id=acc.id):
        date_created = note.data["created_date"]
        doi = _get_note_doi(note)
        has_deposit_record = False
        will_deposit = True
        dr_id = ""
        number_of_notifications += 1
        dr = models.DepositRecord.pull_by_ids(note.id, acc.id)
        if dr:
            has_deposit_record = True
            dr_id = dr.id
            # was this a successful deposit?  if so, don't re-run
            if dr.was_successful():
                will_deposit = False
            else:
                drs = models.DepositRecord.pull_all_by_ids(note.id, acc.id)
                if len(drs) >= app.config.get("MAX_DEPOSIT_ATTEMPTS", 10):
                    print("Notification:{y} for Account:{x} has been attempted {z} times - skipping".format(x=acc.id,
                                                                                                          y=note.id,
                                                                                                          z=len(drs)))
                    will_deposit = False
            if dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge":
                will_deposit = False
        if will_deposit:
                number_to_deposit += 1
        with open(fname2, "a") as f2:
            f2.write(f"{note.id},{doi},{date_created},{has_deposit_record},{dr_id},{will_deposit}\n")
    row = f"{acc.id}, {repository_status.status}, True, {since}, {safe_since}, {number_of_notifications}, {number_to_deposit}\n"
    return row

def debug_run_for_accounts(account_ids):
    today = dates.datetime.today().strftime('%Y-%m-%d')
    path = os.path.join("logs", today)
    os.makedirs(path, exist_ok=True)
    fname = os.path.join(path, "debug_deposit.csv")
    with open(fname, "a") as f:
        f.write(f"Account id, status, try_deposit, since, safe_since, number_of_notifications, number_to_deposit\n")
    for account_id in account_ids:
        row = debug_run_for_account(account_id)
        with open(fname, "a") as f:
            f.write(row)


def _get_note_doi(note):
    doi = []
    for id in note.identifiers:
        if id.get('type', None) == 'doi' and id.get("id", None) is not None:
            doi.append(id["id"])
    return ", ".join(doi)
