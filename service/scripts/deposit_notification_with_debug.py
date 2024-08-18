import sword2
from octopus.modules.jper import client
from octopus.modules.store import store
from octopus.modules.swordv2 import client_http
from octopus.lib import dates
from service import models
from service.deposit import _cache_content

def deposit_notification_with_debug(account_id, notification_id):
    print("Notification: %s" % notification_id)
    print("Account:      %s" % account_id)
    acc = models.Account.pull(account_id)
    j = client.JPER(api_key=acc.api_key)
    note = j.get_notification(notification_id=notification_id)

    deposit_done = False

    deposit_method = 'single zip file'
    if acc.sword_deposit_method == 'individual files':
        deposit_method = acc.sword_deposit_method
    print("Deposit method: %s" % deposit_method)
    if deposit_method != 'single zip file':
        print(f"Deposit method for this account is: {deposit_method}")
        print("This method is only for deposit method 'single zip file'")
        print(f"Deposit status: {deposit_done}")
        print("End of deposit run")
        return deposit_done, None

    # work out if there is a content object to be deposited
    # which means asking the note if there's a content link with a package format supported
    # by the repository
    link = None
    packaging = None
    for p in acc.packaging:
        link = note.get_package_link(p)
        if link is not None:
            packaging = p

    print(f"Link is {link}")
    print(f"packaging is {packaging}")

    if link is None:
        msg = "No content files to deposit for Notification:{y} on Account:{x}".format(x=acc.id, y=note.id)
        print(msg)
        print("Deposit status: {x}".format(x=deposit_done))
        print("End of deposit run")
        return deposit_done, None

    try:
        local_id, path = _cache_content(link, note, acc)
    except client.JPERException as e:
        msg = "Problem while retrieving content from store for SWORD deposit: {x}".format(x=str(e))
        print(msg)
        print(f"Deposit status: {deposit_done}")
        print("End of deposit run")
        return deposit_done, None

    # make a copy of the tmp store for removing the content later
    tmp = store.StoreFactory.tmp()

    if "opus4" in str(packaging).lower() or "escidoc" in str(packaging).lower():
        if "opus4" in str(packaging).lower():
            packaging = None
        elif "escidoc" in str(packaging).lower():
            packaging = "http://purl.org/escidoc/metadata/schemas/0.1/publication"
        print(f"packaging is changed to {packaging}")

    # Not checking deposit record exists
    # Assuming deposit method is simple zip
    print("Not checking if a deposit record already exists")
    dr = models.DepositRecord()
    dr.repository = acc.id
    dr.notification = note.id
    dr.id = dr.makeid()
    dr.deposit_date = dates.now()

    # now we can do the deposit from the locally stored file
    with open(path, "rb") as file_handle:
        msg = "Depositing DeepGreen Package Format:{y} for Account:{x}".format(x=acc.id, y=packaging)
        dr.add_message('info', msg)
        print(msg)

        # create a connection object
        conn = sword2.Connection(user_name=acc.sword_username, user_pass=acc.sword_password,
                                 error_response_raises_exceptions=False, http_impl=client_http.OctopusHttpLayer())
        try:
            ur = conn.create(col_iri=acc.sword_collection, payload=file_handle, filename="deposit.zip",
                             mimetype="application/zip", packaging=packaging)
        except Exception as e:
            msg = "There was an error depositing the package to the repository. {a}".format(a=str(e))
            dr.add_message('error', msg)
            dr.metadata_status = dr.content_status = dr.completed_status = "failed"
            dr.save()
            print(msg)
            print(f"Deposit status: {deposit_done}")
            print("End of deposit run")
            return deposit_done, dr.id

    tmp.delete(local_id)

    # find out if this was an error document, and throw an error if so
    # (recording deposited/failed on the deposit record along the way)
    if isinstance(ur, sword2.Error_Document):
        dr.metadata_status = dr.content_status = dr.completed_status = "failed"
        if not ur.error_href is None:
            if "opus-repository" in ur.error_href and "InvalidXml" in ur.error_href:
                dr.metadata_status = "invalidxml"
            if "opus-repository" in ur.error_href and "PayloadToLarge" in ur.error_href:
                dr.metadata_status = "payloadtoolarge"

        msg1 = "Received error document depositing the package to the repository."
        msg2 = "Content deposit failed with status {x} (error_href={y})".format(x=ur.code, y=ur.error_href)
        msg = "{x}. {y}".format(x=msg1, y=msg2)

        dr.add_message('error', msg)
        dr.save()
        print(f"Deposit status: {deposit_done}")
        print("End of deposit run")
        return deposit_done, dr.id
    else:
        msg = "Content deposit was successful"
        dr.metadata_status = dr.content_status = dr.completed_status = "deposited"
        if app.config.get("STORE_RESPONSE_DATA", False):
            sm.store(dr.id, "content_deposit.txt", source_stream=StringIO(msg))
        dr.add_message('info', msg)
        dr.save()
        print(msg)
        return deposit_done, dr.id


