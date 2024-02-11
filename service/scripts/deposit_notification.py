"""
Script which performes a single deposit
"""

import logging,argparse, sys
from logging import Formatter
from logging.handlers import RotatingFileHandler
from octopus.core import app, initialise, add_configuration
from octopus.modules.jper import client
from service import deposit, models

file_handler = RotatingFileHandler('deposit-notification.log', maxBytes=1000000000, backupCount=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d %(module)s %(funcName)s]'
))
app.logger.addHandler(file_handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",       help="additional configuration to load (e.g. for testing)")
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument("-n", "--notificationid", help="notification of package to be sent", required=True)
    requiredNamed.add_argument("-a", "--accountid",      help="account id of repository SWORD package is sent to", required=True)
    args = parser.parse_args()

    if args.config:
        add_configuration(app, args.config)

    app.config['DEBUG'] = True
    # app.logger.info(app.config)

    initialise()
    app.logger.info("Notification: %s" % args.notificationid)
    app.logger.info("Account:      %s" % args.accountid)

    app.logger.info("Starting SWORDv2 deposit-notification")
    for acc in models.Account.with_sword_activated():
        if acc.id == args.accountid:
            app.logger.info('SWORD activated for account %s' % acc.id)
            j = client.JPER(api_key=acc.api_key)
            note = j.get_notification(notification_id=args.notificationid)
            if note is None:
                app.logger.info('Notification not found')
                sys.exit(3)
            app.logger.info('perform deposit')
            deposit.process_notification(acc, note, since=None, check_deposit_record=False)
            sys.exit(0)

    app.logger.info("Account not found or SWORD not activated for this account")
    sys.exit(3)
