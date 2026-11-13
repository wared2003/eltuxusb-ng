# -*- coding: utf-8 -*-
# Main entry point

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="eltuxusb")
    parser.add_argument('-d', '--debug', action="store_true",
                        help="show useful informations for the developpers (do not write anything to the device)")
    parser.add_argument('-D', '--download',
                        help="download the recordings to a file, ex: /home/user/out.txt")
    parser.add_argument('-R', '--recover',
                        help="!WARNING! reprogram the device configuration from the given file ex: /home/user/config.txt !WARNING!")
    parser.add_argument('-v', '--version', action="store_true",
                        help="show program version and exit")
    args = parser.parse_args()

    if args.version:
        print("eltuxusb version 0.6")
        sys.exit(0)

    if args.debug:
        print("#DEBUG# Starting eltuxusb in debug mode (nothing will be written on the device)")

    if args.download:
        from .el_cmd import el_cmd
        app = el_cmd(path=args.download, debug=args.debug, recover_mode=False)
        app.download()

    elif args.recover:
        from .el_cmd import el_cmd
        app = el_cmd(path=args.recover, debug=args.debug, recover_mode=True)
        app.recover()

    else:
        from .el_ui import EltuxusbApp
        app = EltuxusbApp(debug=args.debug, recover_mode=False)
        sys.exit(app.run(None))


if __name__ == '__main__':
    main()
