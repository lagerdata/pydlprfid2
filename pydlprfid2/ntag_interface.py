import sys
import asyncio
import serial
import logging
from pydlprfid2 import PyDlpRfid2, ISO14443A, ISO14443B, ISO15693#, DLP_CMD, NTAG5_CMD, NTAG5_ADDR
# from crc import CRC

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require('pydlprfid2')[0].version

logger = logging.getLogger(__name__)
manuf_code = "04"

class NtagInterface(PyDlpRfid2):
  def __init__(self):
    super().__init__(serial_port="/dev/ttyUSB0", loglevel=logging.DEBUG)

  def initialize_connection(self):
    self.init_kit()
    self.enable_internal_antenna()
    self.set_protocol()
    self.inventory()
    self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(address=True),
                                command_code='%02X'%M24LR64ER_CMD["SELECT"]["code"],
                                data='0011ABF6580104E0')
    self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code='C0',
                                data='0005')


  def get_status_register(self):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_CONF"]["code"],
                                data = f"{manuf_code}{NTAG5_ADDR['STATUS_REG']['address']:02X}{'01'}")
    print(response)

  def get_ed_config_register(self):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_CONF"]["code"],
                                data = f"{manuf_code}{NTAG5_ADDR['ED_CONFIG_REG']['address']:02X}{'01'}")
    print(response)

  def get_eh_config_register(self):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_CONF"]["code"],
                                data = f"{manuf_code}{NTAG5_ADDR['EH_CONFIG_REG']['address']:02X}{'01'}")
    print(response)

  def read_sram(self, data):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{manuf_code}{NTAG5_ADDR['SRAM_START']['address']:02X}{'40'}")
    print(response)    

  def write_sram(self, string):
    hex_string = write_data.encode().hex()
    formatted_data = hex_string.ljust(64*2, '0')
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["WRITE_SRAM"]["code"],
                                data = f"{manuf_code}{NTAG5_ADDR['SRAM_START']['address']:02X}{formatter_data.upper()}{'40'}")
    hex_string = response.rstrip('0')
    print(bytes.fromhex(hex_string).decode())

  def configure_energyharvesting(self):
    print("#todo")

def ntag_interface_start(argv):
    ntag = NtagInterface()
    

if __name__ == "__main__":
    ntag_interface_start(sys.argv[1:])