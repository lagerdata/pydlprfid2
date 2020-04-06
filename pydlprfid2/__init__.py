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
    print("-r, --read=OFFSET        read one block (hex)")
    print("-s, --readmultiple=OFFSET:BLOCKNUM")
    print("                         read multiple block (hex:hex)")
    print("-g, --getsysinfo         read eeprom info")
    print("-w, --writesingle=OFFSET:DATA")
    print("                         write data in one block")

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hd:p:lu:r:s:vgw:",
                  ["help", "devtty=", "protocol=",
                   "listtag", "uid=", "read=",
                   "verbose", "readmultiple=",
                   "getsysinfo", "writesingle="])
    except getopt.GetoptError:
        usages()
        sys.exit(2)
    
    devtty = None
    listtag = False
    protocol=ISO15693
    uid = None
    blockoffset = None
    blocknum = None
    loglevel = logging.INFO
    getsysinfo = False
    writeoffset = None
    writedata = None
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
            blockoffset = int(arg, 16)
        elif opt in ["-v", "--verbose"]:
            loglevel = logging.DEBUG
        elif opt in ("-s", "--readmultiple"):
            stroffset, strblocknum = arg.split(":")
            blockoffset = int(stroffset, 16)
            blocknum = int(strblocknum, 16)
        elif opt in ("-g", "--getsysinfo"):
            getsysinfo = True
        elif opt in ("-w", "--writesingle"):
            stroffset, strdata = arg.split(":")
            writeoffset = int(stroffset)
            writedata = strdata

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

    if loglevel == logging.DEBUG: # get version only in debug messages level
        reader.get_dlp_rfid2_firmware_version()

    reader.set_protocol(protocol)
    reader.enable_external_antenna()

    if listtag:
        print("Looking for tags")
        uids = list(reader.inventory(single_slot=True))
        if len(uids) == 0:
            print("No tags found")
        else:
            print(f"{len(uids)} tags found")
            for uid, rssi in uids:
                print(f"UID: {uid} RSSI: {rssi}")
    elif getsysinfo:
        values = reader.eeprom_get_system_info(uid)
        print(values)
    elif blockoffset is not None:
        if blocknum is None:
            value = reader.eeprom_read_single_block(uid, blockoffset)
            print(f"Block 0x{blockoffset:02X} : {value}")
        else:
            values = reader.eeprom_read_multiple_block(uid, blocknum, blockoffset)
            print(f"{values}")

