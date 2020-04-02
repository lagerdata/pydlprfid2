import sys
import getopt
import logging
from .pydlprfid2 import PyDlpRfid2, ISO14443A, ISO14443B, ISO15693
from .crc import CRC

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require('pydlprfid2')[0].version

# Logging: Add a null handler to avoid "No handler found" warnings.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

def usages():
    """ print usages """
    print("Usages:")
    print("pdr2 [options]")
    print("-h, --help               print this help")
    print("-d, --devtty filename    uart dev name path")
    print("-p, --protocol PROTOCOL  default ISO15693")

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hd:p:",
                                  ["help", "devtty=", "--protocol="])
    except getopt.GetoptError:
        usages()
        sys.exit(2)
    
    devtty=None
    protocol=ISO15693
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            usages()
            sys.exit(0)
        elif opt in ["-d", "--devtty"]:
            devtty = arg
        elif opt in ["-p", "--protocol"]:
            if arg == "ISO15693":
                protocol = ISO15693
            elif arg == "ISO14443A":
                protocol = ISO14443A
            elif arg == "ISO14443B":
                protocol = ISO14443B

    if devtty is None:
        print("Wrong parameter: Give a devtty path")
        usages()
        sys.exit(2)

    try:
        reader = PyDlpRfid2(serial_port=devtty, debug=True)
    except serial.serialutil.SerialException:
        print(f"Failed to open serial port {devtty}")
        sys.exit(1)

    reader.set_protocol(protocol)
    uids = list(reader.inventory())
    print(uids)

    print("! TODO !")

