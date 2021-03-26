"""
Main script which executes the run cycle.

It will start and remain running until it is shut-down externally, and will execute the deposit.run method
repeatedly.
"""
from octopus.core import app, initialise, add_configuration
import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler('jperswordoutlog', maxBytes=1000000000, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d %(module)s %(funcName)s]'
))
app.logger.addHandler(file_handler)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", help="pycharm debug support enable")
    parser.add_argument("-c", "--config", help="additional configuration to load (e.g. for testing)")
    args = parser.parse_args()

    if args.config:
        add_configuration(app, args.config)

    pycharm_debug = app.config.get('DEBUG_PYCHARM', False)
    if args.debug:
        pycharm_debug = True

    if pycharm_debug:
        app.config['DEBUG'] = False
        import pydevd
        pydevd.settrace(app.config.get('DEBUG_SERVER_HOST', 'localhost'), port=app.config.get('DEBUG_SERVER_PORT', 51234), stdoutToServer=True, stderrToServer=True)
        print("STARTED IN REMOTE DEBUG MODE")

    initialise()

    from service import deposit
    import time, sys

    col_counter = 0
    while True:
        app.logger.info("Starting SWORDv2 Runner")
        deposit.run(fail_on_error=True)

        print(".", end=' ')
        sys.stdout.flush()
        col_counter += 1
        if col_counter >= 36:
            print("")
            col_counter = 0

        time.sleep(app.config.get("RUN_THROTTLE"))
