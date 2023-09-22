import sys
from pydlprfid2.ntag_interface import start_application

if __name__ == "__main__":
    start_application(sys.argv[1:])
