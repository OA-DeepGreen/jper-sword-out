"""
Main workflow engine which carries out the mediation between JPER and the SWORD-enabled 
repositories
"""
import sword2, uuid
from service import xwalk, models
from octopus.modules.store import store
from octopus.modules.jper import client
from octopus.modules.jper import models as jper_models
from io import BytesIO, StringIO
from octopus.modules.swordv2 import client_http
from octopus.core import app
from octopus.lib import dates


class DepositException(Exception):
    """
    Generic exception to be thrown in the case of deposit error
    """
    pass


def run(fail_on_error=True):
    """
    Execute a single pass on all the accounts that have sword activated and process all
    of their notifications since the last time their account was synchronised, until now

    :param fail_on_error: cease execution if an exception is raised
    """
    app.logger.info("Entering run")
    # list all of the accounts that have sword activated
    accs = models.Account.with_sword_activated()

    # process each account
    for acc in accs:
        try:
            process_account(acc)
        except client.JPERException as e:
            app.logger.error("Problem while processing account for SWORD deposit: {x}".format(x=str(e)))
            if fail_on_error:
                raise e
    app.logger.info("Leaving run")


def process_account(acc):
    """
    Retrieve the notifications in JPER associated with this account and relay them on 
    to their sword-enabled repository

    If the account is in status "failing", it will be skipped.

    If the account is in status "problem", and the retry delay has elapsed, it will 
    be re-tried, otherwise it will be skipped

    :param acc: the account whose notifications to process
    """
    app.logger.info("Processing Account:{x}".format(x=acc.id))

    # get the current status of the repository
    repository_status = models.RepositoryStatus.pull(acc.id)

    deposit_log = models.RepositoryDepositLog()
    deposit_log.repository = acc.id

    # if no status record is found, this means the repository is new to 
    # sword deposit, so we need to create one
    if repository_status is None:
        app.logger.debug(
            "Account:{x} has not previously deposited - creating repository status record".format(x=acc.id))
        repository_status = models.RepositoryStatus()
        repository_status.id = acc.id
        repository_status.status = "succeeding"
        repository_status.last_deposit_date = app.config.get("DEFAULT_SINCE_DATE")
        repository_status.save()
        deposit_log.add_message('debug', "First deposit for account {x}".format(x=acc.id), None, None)
    app.logger.info("Status:{x}".format(x=repository_status.status))
    # check to see if we should be continuing with this account (may be failing)
    if repository_status.status == "failing":
        app.logger.debug(
            "Account:{x} is marked as failing - skipping.  You may need to manually reactivate this account".format(
                x=acc.id))
        return

    # check to see if enough time has passed to warrant a re-try (if relevant)
    delay = app.config.get("LONG_CYCLE_RETRY_DELAY")
    if repository_status.status == "problem" and not repository_status.can_retry(delay):
        app.logger.debug(
            "Account:{x} is experiencing problems, and retry delay has not yet elapsed - skipping".format(x=acc.id))
        return

    # Query JPER for the notifications for this account
    since = repository_status.last_deposit_date
    if since is None:
        since = app.config.get("DEFAULT_SINCE_DATE")
        repository_status.last_deposit_date = since

    # 2018-03-14 TD : introduction of 'safety margin' for since 
    # add (or, to be precise, substract) a safety period to 'since' aka 'status.last_deposit_date'
    delta_days = app.config.get("DEFAULT_SINCE_DELTA_DAYS")
    safe_since = dates.format(dates.parse(since) - dates.timedelta(days=delta_days))
    deposit_log.add_message('info', "Finding updated notifications since {x}".format(x=safe_since), None, None)
    deposit_done_count = 0
    # The repository status is recorded after each notification.
    # If any one notification has an error, no further deposits are made,
    # if the notification fails due to a non-specific error
    # What should the status and last deposit date be?
    # FIX ME: Is the above logic correct?
    j = client.JPER(api_key=acc.api_key)
    try:
        # 2018-03-14 TD : use now the safety net safe_since instead
        for note in j.iterate_notifications(safe_since, repository_id=acc.id):
            try:
                # 2018-03-08 TD : introducing a return value 'deposit_done' ....
                deposit_done, deposit_record_id = process_notification(acc, note, since=None)
                # if the notification is successfully processed, record the new last_deposit_date
                # status.last_deposit_date = note.analysis_date
                # 2018-03-06 TD : 'note.analysis_date' seems to produce nasty instabilities
                #                 and, most importantly, missed notifications.
                #                 Here, we try 'note.created_date' instead.  Might cause
                #                 a bit of double working, but hey, it will be checked
                #                 in 'process_notification(...)' anyway.
                # status.last_deposit_date = note.created_date
                if deposit_done is True:
                    # FIX ME. Why is deposit date set to notification created date and not the current date?
                    repository_status.last_deposit_date = note.data["created_date"]
                    deposit_log.add_message('info', "Notification deposited", note.id, deposit_record_id)
                    deposit_done_count += 1
                else:
                    drec = models.DepositRecord.pull(deposit_record_id)
                    if drec and (drec.metadata_status == "invalidxml" or drec.metadata_status == "payloadtoolarge"):
                        deposit_log.add_message('warn',
                                                "Notification not deposited - {x}".format(x=drec.metadata_status),
                                                note.id, deposit_record_id)
                #     # Too many notifications get retried. So not adding this
                #     deposit_log.add_message('debug', "Notification not deposited", note.id, deposit_record_id)
            except DepositException as e:
                msg1 = "Received package deposit exception for Notification:{y} on Account:{x}. ".format(
                    x=acc.id, y=note.id)
                msg2 = "Recording a failed deposit and ceasing further processing of notifications for this account."
                app.logger.error(msg1 + msg2)
                msg = "{x} {y} {z}".format(x=msg1, y=msg2, z=str(e))
                deposit_log.add_message('error', msg, note.id, None)
                if deposit_done_count > 0:
                    deposit_log.add_message('info', "Number of successful deposits: {x}".format(x=deposit_done_count),
                                            None, None)
                # record the failure against the status object
                limit = app.config.get("LONG_CYCLE_RETRY_LIMIT")
                repository_status.record_failure(limit)
                repository_status.save()
                deposit_log.status = repository_status.status
                deposit_log.save()
                return
    except client.JPERException as e:
        # save the status where we currently got to, so we can pick up again later
        repository_status.save()
        msg = "Problem while processing account for SWORD deposit: {x}".format(x=str(e))
        app.logger.error(msg)
        deposit_log.add_message('error', msg, None, None)
        if deposit_done_count > 0:
            deposit_log.add_message('info', "Number of successful deposits: {x}".format(x=deposit_done_count), None,
                                    None)
        deposit_log.status = repository_status.status
        deposit_log.save()
        raise e

    # if we get to here, all the notifications for this account have been deposited, 
    # and we can update the status and finish up
    repository_status.save()
    if deposit_done_count > 0:
        deposit_log.add_message('info', "Number of successful deposits: {x}".format(x=deposit_done_count), None, None)
        deposit_log.status = "succeeding"
        deposit_log.save()
    app.logger.info("Leaving processing account")
    return


def process_notification(acc, note, since):
    """
    For the given account and notification, deliver the notification to 
    the sword-enabled repository.

    The since date is required to check for duplication of notifications, 
    this will avoid situations where the granularity of the since date and 
    the last_deposit_date are too large and there are some processed and 
    some unprocessed notifications all with the same timestamp

    :param acc: user account of repository
    :param note: notification to be deposited
    :param since: earliest date which the current set of requests is made from.
    :return: flag (boolean) to indicated a successful deposit
    """
    app.logger.debug("Processing Notification:{y} for Account:{x}".format(x=acc.id, y=note.id))

    # for type inspection...
    assert isinstance(acc, models.Account)
    assert isinstance(note, jper_models.OutgoingNotification)

    # 2018-03-08 TD : new return flag; initialised to 'False'
    deposit_done = False

    # first thing is to check the note for proximity to the since date, and check 
    # whether we did them already this will avoid situations where the granularity 
    # of the since date and the last_deposit_date are too large and there are some 
    # processed and some unprocessed notifications all with the same timestamp
    # if note.analysis_date == since:
    # 2018-03-07 TD : this is to match the change in 'process_account(...)' (the caller)
    # if note.data["created_date"] == since:
    # 2018-03-07 TD : completely taking out the if-clause;
    #                 therefore, testing every call for possible doubles!
    # this gets the most recent deposit record for this id pair
    dr = models.DepositRecord.pull_by_ids(note.id, acc.id)

    if dr is None:
        # make a deposit record object to record the events
        dr = models.DepositRecord()
        dr.repository = acc.id
        dr.notification = note.id
        dr.id = dr.makeid()
    else:
        # was this a successful deposit?  if so, don't re-run
        if dr.was_successful():
            app.logger.debug(
                "Notification:{y} for Account:{x} was previously deposited - skipping".format(x=acc.id, y=note.id))
            # 2018-03-08 TD : return the new flag with 'False'
            return deposit_done, dr.id
        # 2020-01-09 TD : check for a special case 'invalidxml' (induced by a sloppy 
        #                 OPUS4 sword implementation; fixed in v4.7.x or higher)
        # 2020-01-13 TD : ... and special case 'payloadtoolarge'
        if dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge":
            app.logger.debug(
                "Notification:{y} for Account:{x} was not previously deposited - SPECIAL CASE ('{z}') - skipping".format(
                    x=acc.id, y=note.id, z=dr.metadata_status))
            # 2020-01-09 TD : return also 'False' in this special case
            return deposit_done, dr.id

    # set the deposit date to current date and time
    dr.deposit_date = dates.now()

    # work out if there is a content object to be deposited
    # which means asking the note if there's a content link with a package format supported
    # by the repository
    link = None
    packaging = None
    for p in acc.packaging:
        link = note.get_package_link(p)
        if link is not None:
            packaging = p

    # pre-populate the content and completed bits of the deposit record, 
    # if there is no package to be deposited
    if link is None:
        dr.content_status = "none"
        dr.completed_status = "none"

    url = link['url'].replace('https://www.oa-deepgreen.de', 'http://li31.int.zib.de')
    url = link['url'].replace('https://test.oa-deepgreen.de', 'http://li31.int.zib.de')
    link['url'] = url

    # 2017-05-19 TD : major insert of different repository cases: OPUS4, Pubman(ESciDoc), DSpace, ???, ...
    # 2017-07-13 TD : just added MODS as further repository format option
    # 2019-08-14 TD : added the SimpleZip as another format option to the list...
    if "opus4" in str(packaging).lower() or \
            "escidoc" in str(packaging).lower() or \
            "dspace" in str(packaging).lower() or \
            "mods" in str(packaging).lower() or \
            "simple" in str(packaging).lower():
        # this should never happen, but just in case, if there's no content to deposit we can
        # wrap up and return
        if link is None:
            msg = "No content files to deposit for Notification:{y} on Account:{x}".format(x=acc.id, y=note.id)
            dr.add_message("debug", msg)
            app.logger.debug(msg)
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()
            # 2018-03-08 TD : return with the new flag (currently 'False' up to here, hopefully!
            return deposit_done, dr.id

        # first, get a copy of the file from the API into the local tmp store
        # Not raising an exception, just recording it and returning deposit not done
        try:
            local_id, path = _cache_content(link, note, acc)
        except client.JPERException as e:
            msg = "Problem while retrieving content from store for SWORD deposit: {x}".format(x=str(e))
            dr.add_message('error', msg)
            app.logger.error(msg)
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()
            return deposit_done, dr.id

        # make a copy of the tmp store for removing the content later
        tmp = store.StoreFactory.tmp()

        # adjust some special case(s) for the packaging identification string.
        # Some repositories are really picky about this...
        # 2019-03-05 TD : it turned out that our DSpace test repo only accepts METSDSpaceSIP
        #                 as packaging string, and sorts out the correct format by itself then 
        # 2020-02-05 TD : someone seemed to have corrected for the packaging string... dumb.
        #                 to work around just commenting out the workaround, sigh.
        if "opus4" in str(packaging).lower():
            packaging = None
        elif "escidoc" in str(packaging).lower():
            packaging = "http://purl.org/escidoc/metadata/schemas/0.1/publication"
        # elif "metsmods" in str(packaging).lower():
        #    packaging = "http://purl.org/net/sword/package/METSDSpaceSIP"

        # now we can do the deposit from the locally stored file 
        # (which we need because we're going to use seek() on it 
        #                  which we can't do with the http stream)
        with open(path, "rb") as f:
            try:
                deepgreen_deposit(packaging, f, acc, dr)
                # ensure the content status is set as we expect it
                dr.metadata_status = dr.content_status = dr.completed_status = "deposited"
                # 2018-03-08 TD : And we had a lift off...
                deposit_done = True
            except DepositException as e:
                # save the actual deposit record, ensuring the content_status is set the way
                # we expect
                # 2020-01-09 TD : treat special case 'invalidxml' separately
                # 2020-01-13 TD : ... and special case 'payloadtoolarge'
                dr.content_status = "failed"
                if not (dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge"):
                    dr.metadata_status = "failed"
                if app.config.get("STORE_RESPONSE_DATA", False):
                    dr.save()

                # delete the locally stored content
                tmp.delete(local_id)

                # 2020-01-09 TD : do not kick the exception upstairs but simply return Flag!
                if dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge":
                    # app.logger.info("Leaving processing notifs (with '{z}')".format(z=dr.metadata_status))
                    return deposit_done, dr.id

                msg1 = "Received package deposit exception for Notification:{y} on Account:{x}.".format(
                    x=acc.id, y=note.id)
                msg2 = "Recording a failed deposit and ceasing processing on this notification"
                app.logger.error("{x} {y}".format(x=msg1, y=msg2))
                # kick the exception upstairs for continued handling
                raise e

        # now we can get rid of the locally stored content
        tmp.delete(local_id)

    else:
        # make the metadata deposit, determining whether to immediately
        # complete the deposit if there is no link for content
        try:
            receipt = metadata_deposit(note, acc, dr, complete=link is None)
            # ensure the metadata status is set as we expect it
            dr.metadata_status = "deposited"
            # 2018-03-08 TD : depositing metadata counts as well!
            deposit_done = True
        except DepositException as e:
            # save the actual deposit record, ensuring that the metadata_status is set 
            # the way we expect
            # 2020-01-09 TD : treat special case 'invalidxml' separately
            # 2020-01-13 TD : ... and special case 'payloadtoolarge'
            if not dr.metadata_status == "invalidxml" and not dr.metadata_status == "payloadtoolarge":
                dr.metadata_status = "failed"
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()

            # 2020-01-09 TD : do not kick the exception upstairs but simply return Flag!
            if dr.metadata_status == "invalidxml" or dr.metadata_status == "payloadtoolarge":
                app.logger.info("Leaving processing notifs (with '{z}')".format(z=dr.metadata_status))
                return deposit_done, dr.id

            msg1 = "Received metadata deposit exception for Notification:{y} on Account:{x}.".format(
                x=acc.id, y=note.id)
            msg2 = "Recording a failed deposit and ceasing processing on this notification"
            app.logger.error("{x} {y}".format(x=msg1, y=msg2))
            # kick the exception upstairs for continued handling
            raise e

        # beyond this point, we are only dealing with content, so if there's no content
        # to deposit we can wrap up and return
        if link is None:
            msg = "No content files to deposit for Notification:{y} on Account:{x}".format(x=acc.id, y=note.id)
            dr.add_message('debug', msg)
            app.logger.debug(msg)
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()
            # 2018-03-08 TD : return with flag
            return deposit_done, dr.id

        # if we get to here, we have to deal with the content deposit

        # first, get a copy of the file from the API into the local tmp store
        try:
            local_id, path = _cache_content(link, note, acc)
        except client.JPERException as e:
            msg = "Problem while retrieving content from store for SWORD deposit: {x}".format(x=str(e))
            dr.add_message('error', msg)
            app.logger.error(msg)
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()
            return deposit_done, dr.id

        # make a copy of the tmp store for removing the content later
        tmp = store.StoreFactory.tmp()

        # now we can do the deposit from the locally stored file (which we need because we're going to use seek() on it
        # which we can't do with the http stream)
        with open(path, "rb") as f:
            try:
                package_deposit(receipt, f, packaging, acc, dr)
                # ensure the content status is set as we expect it
                dr.content_status = "deposited"
                # 2018-03-08 TD : ... and a successful deposit, again!
                deposit_done = True
            except DepositException as e:
                msg1 = "Received package deposit exception for Notification:{y} on Account:{x}.".format(
                    x=acc.id, y=note.id)
                msg2 = "Recording a failed deposit and ceasing processing on this notification"
                app.logger.error("{x} {y}".format(x=msg1, y=msg2))
                # save the actual deposit record, ensuring the content_status is set the way we expect
                dr.content_status = "failed"
                if app.config.get("STORE_RESPONSE_DATA", False):
                    dr.save()

                # delete the locally stored content
                tmp.delete(local_id)

                # kick the exception upstairs for continued handling
                raise e

        # now we can get rid of the locally stored content
        tmp.delete(local_id)

        # finally, complete the request
        try:
            complete_deposit(receipt, acc, dr)
            # ensure the completed status is set as we expect it
            dr.completed_status = "deposited"
            # 2018-03-08 TD : set the return flag to 'True'
            deposit_done = True
        except DepositException as e:
            msg1 = "Received complete request exception for Notification:{y} on Account:{x}.".format(x=acc.id,
                                                                                                     y=note.id)
            msg2 = "Recording a failed deposit and ceasing processing on this notification"
            app.logger.error("{x} {y}".format(x=msg1, y=msg2))

            # save the actual deposit record, ensuring the completed_status is set the way we expect
            dr.completed_status = "failed"
            if app.config.get("STORE_RESPONSE_DATA", False):
                dr.save()

            # kick the exception upstairs for continued handling
            raise e
    #
    # 2017-05-19 TD : End of all repository cases here ...
    #

    # that's it, we've successfully deposited this notification to the repository along with all its content
    if app.config.get("STORE_RESPONSE_DATA", False):
        dr.save()
    app.logger.debug("Leaving processing notification")
    # 2018-03-08 TD : return with (new) flag
    return deposit_done, dr.id


def _cache_content(link, note, acc):
    """
    Make a local copy of the content referenced by the link

    This will copy the content retrieved via the link into the temp store for use in the onward relay

    :param link: url to content
    :param note: notification we are working on
    :param acc: user account we are working as
    """
    app.logger.debug("Entering _cache_content")
    j = client.JPER(api_key=acc.api_key)
    try:
        gen, headers = j.get_content(link.get("url"))
    except client.JPERException as e:
        raise e

    local_id = uuid.uuid4().hex
    tmp = store.StoreFactory.tmp()
    tmp.store(local_id, "README.txt", source_stream=StringIO(note.id))
    fn = link.get("url").split("/")[-1]
    out = tmp.path(local_id, fn, must_exist=False)

    with open(out, "wb") as f:
        for chunk in gen:
            if chunk:
                f.write(chunk)
            else:
                break

    app.logger.debug("Leaving _cache_content")
    return local_id, out


#
# 2017-05-19 TD : For the time being, DeepGreen wants to deposit all in once.
#
def deepgreen_deposit(packaging, file_handle, acc, deposit_record):
    """
    Deposit the binary package content to the target repository

    :param packaging: the package format identifier
    :param file_handle: the file handle on the binary content to deliver
    :param acc: the account we are working as
    :param deposit_record: provenance object for recording actions during this deposit process
    """
    msg = "Depositing DeepGreen Package Format:{y} for Account:{x}".format(x=acc.id, y=packaging)
    deposit_record.add_message('info', msg)
    app.logger.info(msg)

    # create a connection object
    conn = sword2.Connection(user_name=acc.sword_username, user_pass=acc.sword_password,
                             error_response_raises_exceptions=False, http_impl=client_http.OctopusHttpLayer())

    #
    # this one would create an collection item as the package's file(s)
    try:
        ur = conn.create(col_iri=acc.sword_collection, payload=file_handle, filename="deposit.zip",
                         mimetype="application/zip", packaging=packaging)
    except Exception as e:
        msg = "There was an error depositing the package to the repository. {a}".format(a=str(e))
        deposit_record.add_message('error', msg)
        app.logger.error("{x}. Raising DepositException".format(x=msg))
        raise DepositException(msg)

    # storage manager instance
    sm = store.StoreFactory.get()

    # find out if this was an error document, and throw an error if so
    # (recording deposited/failed on the deposit_record along the way)
    if isinstance(ur, sword2.Error_Document):
        deposit_record.content_status = "failed"
        if not ur.error_href is None:
            if "opus-repository" in ur.error_href and "InvalidXml" in ur.error_href:
                deposit_record.metadata_status = "invalidxml"
            if "opus-repository" in ur.error_href and "PayloadToLarge" in ur.error_href:
                deposit_record.metadata_status = "payloadtoolarge"

        msg1 = "Received error document depositing the package to the repository."
        msg2 = "Content deposit failed with status {x} (error_href={y})".format(x=ur.code, y=ur.error_href)
        msg = "{x}. {y}".format(x=msg1, y=msg2)
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "content_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('error', msg)
        app.logger.error("{x} - raising DepositException".format(x=msg))
        raise DepositException(msg)
    else:
        msg = "Content deposit was successful"
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "content_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('info', msg)
        deposit_record.content_status = "deposited"
        app.logger.info(msg)

    app.logger.debug("DeepGreen Package deposit")
    return


def metadata_deposit(note, acc, deposit_record, complete=False):
    """
    Deposit the metadata from the notification in the target repository

    :param note: the notification to be deposited
    :param acc: the account we are working as
    :param deposit_record: provenance object for recording actions during this deposit process
    :param complete: True/False; should we tell the repository that the deposit process is complete (do this if there is no binary deposit to follow)
    :return: the deposit receipt from the sword client
    """
    msg = "Depositing metadata for Notification:{y} for Account:{x}".format(x=acc.id, y=note.id)
    deposit_record.add_message('info', msg)
    app.logger.info(msg)

    # create a connection object
    conn = sword2.Connection(user_name=acc.sword_username, user_pass=acc.sword_password,
                             error_response_raises_exceptions=False, http_impl=client_http.OctopusHttpLayer())

    # storage manager instance for use later
    sm = store.StoreFactory.get()

    # assemble the atom entry for deposit
    entry = sword2.Entry()
    xwalk.to_dc_rioxx(note, entry)

    # do the deposit
    ip = not complete
    if acc.repository_software in ["eprints"]:
        # EPrints doesn't allow "complete" requests, so we leave everything in_progress for the purposes of consistency
        ip = True

    try:
        receipt = conn.create(col_iri=acc.sword_collection, metadata_entry=entry, in_progress=ip)
    except Exception as e:
        msg = "There was an error depositing the metadata to the repository. {a}".format(a=str(e))
        deposit_record.add_message('error', msg)
        app.logger.error("{x}. Raising DepositException".format(x=msg))
        raise DepositException(msg)

    # if the receipt has a dom object, store it (it may be a deposit receipt or an error)
    if receipt.dom is not None and app.config.get("STORE_RESPONSE_DATA", False):
        content = receipt.to_xml()
        sm.store(deposit_record.id, "metadata_deposit_response.xml", source_stream=BytesIO(content))

    # find out if this was an error document, and throw an error if so
    # (recording deposited/failed on the deposit_record along the way)
    if isinstance(receipt, sword2.Error_Document):
        deposit_record.metadata_status = "failed"
        # 2020-01-09 TD : check for special cases for 'InvalidXml' in the error document
        # ehref = receipt.error_href
        # 2020-01-13 TD : safety check, e.g. if receipt.code == 500 (INTERNAL SERVER ERROR),
        #                                    then receipt.error_href is None
        if not receipt.error_href is None:
            if "opus-repository" in receipt.error_href and "InvalidXml" in receipt.error_href:
                deposit_record.metadata_status = "invalidxml"
            # 2020-01-13 TD : check for special cases for 'PayloadToLarge' in the error document
            #                 (note the typo here in OPUS4 ...)
            if "opus-repository" in receipt.error_href and "PayloadToLarge" in receipt.error_href:
                deposit_record.metadata_status = "payloadtoolarge"

        msg1 = "Received error document depositing metadata to the repository."
        msg2 = "Metadata deposit failed with status {x} (error_href={y})".format(x=receipt.code, y=receipt.error_href)
        msg = "{x}. {y}".format(x=msg1, y=msg2)
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "metadata_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('error', msg)
        app.logger.error("{x} - raising DepositException".format(x=msg))
        raise DepositException(msg)
    else:
        msg = "Metadata deposit was successful"
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "metadata_deposit.txt", source_stream=StringIO(msg))
        deposit_record.metadata_status = "deposited"
        deposit_record.add_message('info', msg)
        app.logger.info(msg)

    # if this wasn't an error document, then we have a legitimate response, but we need the deposit receipt
    # so get it explicitly, and store it
    if receipt.dom is None:
        try:
            receipt = conn.get_deposit_receipt(receipt.edit)
        except Exception as e:
            msg = "There was an error attempting to retrieve deposit receipt in repository. {x}".format(x=str(e))
            deposit_record.add_message('error', msg)
            app.logger.error(msg)
            raise DepositException(msg)
        if app.config.get("STORE_RESPONSE_DATA", False):
            content = receipt.to_xml()
            sm.store(deposit_record.id, "metadata_deposit_response.xml", source_stream=StringIO(content))

    # if this is an eprints repository, also send the XML as a file
    if acc.repository_software in ["eprints"]:
        xmlhandle = StringIO(str(entry))
        try:
            conn.add_file_to_resource(receipt.edit_media, xmlhandle, "sword.xml", "text/xml")
        except Exception as e:
            msg = "There was an error attempting to deposit atom entry as file in Eprints repository. {x}".format(
                x=str(e))
            deposit_record.add_message('error', msg)
            app.logger.error(msg)
            raise DepositException(msg)

    app.logger.info("Leaving metadata deposit")
    return receipt


def package_deposit(receipt, file_handle, packaging, acc, deposit_record):
    """
    Deposit the binary package content to the target repository

    :param receipt: deposit receipt from the metadata deposit
    :param file_handle: the file handle on the binary content to deliver
    :param packaging: the package format identifier
    :param acc: the account we are working as
    :param deposit_record: provenance object for recording actions during this deposit process
    """
    msg = "Depositing Package of Format:{y} for Account:{x}".format(x=acc.id, y=packaging)
    deposit_record.add_message('info', msg)
    app.logger.info(msg)

    # create a connection object
    conn = sword2.Connection(user_name=acc.sword_username, user_pass=acc.sword_password,
                             error_response_raises_exceptions=False, http_impl=client_http.OctopusHttpLayer())

    # FIXME: not that neat, but eprints has special behaviours that we need to accommodate.  So, in the eprints
    # case we add the package as a file to the resource, but in all other cases we append the files to the item
    if acc.repository_software in ["eprints"]:
        # this one adds the package as a new file to the item
        try:
            ur = conn.add_file_to_resource(receipt.edit_media, file_handle, "deposit.zip", "application/zip", packaging)
        except Exception as e:
            msg = "There was an error attempting to deposit file in repository to Eprints. {x}".format(x=str(e))
            deposit_record.add_message('error', msg)
            app.logger.error("{x} - raising DepositException".format(x=msg))
            raise DepositException(msg)
    else:
        # this one would replace all the binary files
        try:
            ur = conn.update_files_for_resource(file_handle, "deposit.zip", mimetype="application/zip",
                                                packaging=packaging, dr=receipt)
        except Exception as e:
            msg = "There was an error attempting to deposit file in repository. {x}".format(x=str(e))
            deposit_record.add_message('error', msg)
            app.logger.error("{x} - raising DepositException".format(x=msg))
            raise DepositException(msg)

        # this one would append the package's files to the resource
        # ur = conn.append(payload=file_handle, filename="deposit.zip",
        # mimetype="application/zip", packaging=packaging, dr=receipt)

    # storage manager instance
    sm = store.StoreFactory.get()

    # find out if this was an error document, and throw an error if so
    # (recording deposited/failed on the deposit_record along the way)
    if isinstance(ur, sword2.Error_Document):
        deposit_record.content_status = "failed"
        msg1 = "Received error document depositing package to the repository."
        msg2 = "Content deposit failed with status {x} (error_href={y})".format(x=ur.code, y=ur.error_href)
        msg = "{x}. {y}".format(x=msg1, y=msg2)
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "content_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('error', msg)
        app.logger.error("{x} - raising DepositException".format(x=msg))
        raise DepositException(msg)
    else:
        msg = "Content deposit was successful"
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "content_deposit.txt", source_stream=StringIO(msg))
        deposit_record.content_status = "deposited"
        deposit_record.add_message('info', msg)
        app.logger.info(msg)

    app.logger.debug("Package deposit")
    return


def complete_deposit(receipt, acc, deposit_record):
    """
    Issue a "complete" request against the repository, to indicate that no further files are coming

    :param receipt: deposit receipt from previous metadata deposit
    :param acc: account we are working as
    :param deposit_record: provenance object for recording actions during this deposit process
    """
    msg = "Sending complete request for Account:{x}".format(x=acc.id)
    deposit_record.add_message('info', msg)
    app.logger.info(msg)

    # EPrints repositories can't handle the "complete" request
    cr = None
    if acc.repository_software not in ["eprints"]:
        # create a connection object
        conn = sword2.Connection(user_name=acc.sword_username, user_pass=acc.sword_password,
                                 error_response_raises_exceptions=False, http_impl=client_http.OctopusHttpLayer())

        # send the complete request to the repository
        try:
            cr = conn.complete_deposit(dr=receipt)
        except Exception as e:
            msg = "There was an error attempting to complete deposit in repository. {x}".format(x=str(e))
            deposit_record.add_message('error', msg)
            app.logger.error("{x} - raising DepositException".format(x=msg))
            raise DepositException(msg)

    # storage manager instance
    sm = store.StoreFactory.get()

    # find out if this was an error document, and throw an error if so
    # (recording deposited/failed on the deposit_record along the way)
    if cr is None:
        deposit_record.completed_status = "none"
        msg = "Complete request ignored, as repository is '{x}' which does not support this operation".format(
            x=acc.repository_software)
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "complete_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('debug', msg)
    elif isinstance(cr, sword2.Error_Document):
        deposit_record.completed_status = "failed"
        msg1 = "Received error document for complete request for the repository."
        msg2 = "Complete request failed with status {x} (error_href={y})".format(x=cr.code, y=cr.error_href)
        msg = "{x}. {y}".format(x=msg1, y=msg2)
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "complete_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('error', msg)
        app.logger.error("{x} - raising DepositException".format(x=msg))
        raise DepositException(msg)
    else:
        msg = "Complete request was successful"
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(deposit_record.id, "complete_deposit.txt", source_stream=StringIO(msg))
        deposit_record.add_message('info', msg)
        deposit_record.completed_status = "deposited"
        app.logger.info(msg)

    app.logger.debug("Leaving complete deposit")
    return
