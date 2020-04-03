import sys
import getopt
import serial
import logging
from .pydlprfid2 import PyDlpRfid2, ISO14443A, ISO14443B, ISO15693
from .crc import CRC

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require('pydlprfid2')[0].version

def usages():
    """ print usages """
    print("Usages:")
    print("pdr2 [options]")
    print("-h, --help               print this help")
    print("-v, --verbose            print more messages")
    print("-d, --devtty=filename    uart dev name path")
    print("-p, --protocol=PROTOCOL  default ISO15693")
    print("-l, --listtag            list tag present")
    print("-u, --uid=UID            give UID to access")
    print("-r, --read=BLOCKNUM      read one block")

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hd:p:lu:r:v",
                  ["help", "devtty=", "protocol=",
                   "listtag", "uid=", "read=",
                   "verbose"])
    except getopt.GetoptError:
        usages()
        sys.exit(2)
    
    devtty = None
    listtag = False
    protocol=ISO15693
    uid = None
    blocknum = None
    loglevel = logging.INFO
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
        elif opt in ["-l", "--listtag"]:
            listtag = True
        elif opt in ["-u", "--uid"]:
            uid = arg
        elif opt in ["-r", "--read"]:
            blocknum = int(arg)
        elif opt in ["-v", "--verbose"]:
            loglevel = logging.DEBUG

    if devtty is None:
        print("Wrong parameter: Give a devtty path")
        usages()
        sys.exit(2)

    print("Initilize DLP")
    try:
        reader = PyDlpRfid2(serial_port=devtty, loglevel=loglevel)
    except serial.serialutil.SerialException:
        print(f"Failed to open serial port {devtty}")
        sys.exit(1)

    reader.set_protocol(protocol)
    reader.enable_external_antenna()

    if listtag:
        print("Looking for tags")
        uids = list(reader.inventory())
        if len(uids) == 0:
            print("No tags found")
        else:
            print(f"{len(uids)} tags found")
            for uid, rssi in uids:
                print(f"UID: {uid} RSSI: {rssi}")
    elif blocknum is not None:
        if uid is None:
            print("Please give the UID")
            sys.exit(1)
        value = reader.eeprom_read_single_block(uid, blocknum)
        print(f"Block {blocknum} : {value}")
