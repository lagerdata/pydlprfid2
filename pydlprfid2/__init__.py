import sys
import getopt
import logging
from .pydlprfid2 import PyRFIDGeek, ISO14443A, ISO14443B, ISO15693
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
    print("-h, --help             print this help")
    print("-d, --devtty filename  uart dev name path")

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hd:",
                                  ["help", "devtty="])
    except getopt.GetoptError:
        usages()
        sys.exit(2)
    
    devtty=None
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            usages()
            sys.exit(0)
        elif opt in ["-d", "--devtty"]:
            devtty = arg

    if devtty is None:
        print("Wrong parameter: Give a devtty path")
        usages()
        sys.exit(2)

    print("! TODO !")

