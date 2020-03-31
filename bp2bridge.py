#! /usr/bin/python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Author:   Fabien Marteau <fabien.marteau@armadeus.com>
# Created:  31/03/2020
#-----------------------------------------------------------------------------
#  Copyright (2020)  Armadeus Systems
#-----------------------------------------------------------------------------
""" bp2bridge
"""

import sys
import time
import getopt
import serial

class Bp2Bridge(object):
    """ Set bus pirate as a standard UART controller
    """
    BAUDRATE=115200
    def __init__(self, devpath):
        self.devpath = devpath

    def to_bridge(self):
        with serial.Serial(self.devpath, self.BAUDRATE, timeout=2) as ser:
            ser.write(b"\n")
            ret = ser.read()
            ser.write(b"m3\n")
            ret = ser.read()
            ser.write(b"9\n") # 115200 bps
            ret = ser.read()
            for i in range(3):
                ser.write(b"1\n")
                ret = ser.read()
            ser.write(b"2\n") # output ttl
            ret = ser.read()
            ser.write(b"W\n") # power on
            ret = ser.read()
            ser.write(b"(1)\n") # set macro for bridge
            ret = ser.read()
            ser.write(b"y") # agreed
            ret = ser.read()
            # ok for bridge

def usage():
    """ print help """
    print("Usage:")
    print("$ python3 bp2bridge.py [uartdevpath]")
    print("-h, --help       print this message")
    print("-d, --devpath    give the uart device path")

if __name__ == "__main__":
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:",
                                   ["help", "devpath="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    devpath = None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in ("-d", "devpath"):
            devpath = arg

    if devpath is None:
        raise Exception("give uart path")

    bb = Bp2Bridge(devpath)
    bb.to_bridge()
    print("{} is now configured as standard tty uart ({})"
            .format(devpath, bb.BAUDRATE))
