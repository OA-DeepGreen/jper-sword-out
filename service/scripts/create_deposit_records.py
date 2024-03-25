from service.models import DepositRecord, RepositoryDepositLog
from octopus.lib import dates
import os, csv, sys

def create_deposit_record(repository_id, notification_id):
    dr = DepositRecord()
    dr.repository = repository_id
    dr.notification = notification_id
    dr.id = dr.makeid()
    # set the deposit date to current date and time
    dr.deposit_date = dates.now()
    dr.metadata_status = dr.content_status = dr.completed_status = "deposited"
    message = "Notification not needed by repository"
    dr.add_message('info', message)
    dr.save()
    return dr.id

def create_deposit_log_for_csv(repository_id, notification_csv_file):
    if not os.path.isfile(notification_csv_file):
        print('file does not exist #{f}'.format(f=notification_csv_file))
        return False
    deposit_log = RepositoryDepositLog()
    deposit_log.repository = repository_id
    deposit_log.add_message('info', "Proxy deposit for account {x}".format(x=repository_id), None, None)
    count = 0
    with open(notification_csv_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            deposit_record_id = create_deposit_record(repository_id, row['notification_id'])
            deposit_log.add_message('info', "Notification deposited", row['notification_id'], deposit_record_id)
            count += 1
    deposit_log.status = "succeeding"
    deposit_log.add_message('info', "Number of successful deposits: {x}".format(x=count), None,
                            None)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: create_deposit_records.py <repository_id> <notification_ids_csv_file>\n CSV file has to have column <notification_id>.')
        exit()

    repository_id = sys.argv[1]
    csf_file = sys.argv[2]
    print('Starting creating logs for {repository_id}'.format(repository_id=repository_id))
    create_deposit_log_for_csv(csf_file, repository_id)
    print('Done creating logs for {repository_id}'.format(repository_id=repository_id))

