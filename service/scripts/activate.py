from octopus.core import app, add_configuration
from service import control

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    # some general script running features
    parser.add_argument("-d", "--debug", action="store_true", help="pycharm debug support enable")
    parser.add_argument("-c", "--config", help="additional configuration to load (e.g. for testing)")
    parser.add_argument("-r", "--repo", help="id of the repository account to affect")
    parser.add_argument("-a", "--activate", help="activate the deposit process for this account (e.g. if it has been automatically suspended)", action="store_true")
    parser.add_argument("-s", "--stop", help="stop/deactivate the deposit process for this account", action="store_true")

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

    if not args.repo:
        parser.print_help()
        exit(0)

    if args.activate and args.stop:
        print("Please specify only one of -a/--activate and -s/--stop")
        parser.print_help()
        exit(0)

    if args.stop:
        control.deactivate_deposit(args.repo)
    elif args.activate:
        control.activate_deposit(args.repo)
