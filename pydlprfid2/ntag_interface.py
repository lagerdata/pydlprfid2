import sys
import asyncio
import serial
import logging
import re
import time
from pydlprfid2 import PyDlpRfid2, ISO14443A, ISO14443B, ISO15693#, DLP_CMD, NTAG5_CMD, NTAG5_ADDR
# from crc import CRC

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require('pydlprfid2')[0].version

logger = logging.getLogger(__name__)
manuf_code = "04"

DLP_CMD = {
        "DIRECTMODE":   {"code": '0F', "desc": "Direct mode"},
        "WRITESINGLE":  {"code": '10', "desc": "Write single"},
        "WRITECONTINU": {"code": '11', "desc": "Write Continuous"},
        "READSINGLE":   {"code": '12', "desc": "Read single"},
        "READCONTINU":  {"code": '13', "desc": "Read Continuous"},
        "ANTICOL15693": {"code": '14', "desc": "ISO15693 anticollision"},
        "DIRECTCMD":    {"code": '15', "desc": "Direct command"},
        "RAWWRITE":     {"code": '16', "desc": "Raw write"},
        "REQUESTCMD":   {"code": '18', "desc": ("Everything after the 18 is what is"
                                              "actually transmitted over the air")},
        "INTERNANT": {"code": '2A', "desc": "Enable internal antenna"},
        "EXTERNANT": {"code": '2B', "desc": "Enable external antenna"},
        "GPIOMUX":   {"code": '2C', "desc": "GPIO multiplexer config"},
        "GPIOCFG":   {"code": '2D', "desc": "GPIO terminaison config"},

        "NFCT2CMD":   {"code": '72', "desc": "NFC Type 2 command"},

        "REQA14443A": {"code": 'A0', "desc": "ISO14443A Anticollision REQA"},
        "WUPA14443A": {"code": 'A1', "desc": "ISO14443A Anticollision WUPA"},
        "SEL14443A":  {"code": 'A2', "desc": "ISO14443A Select"},
        "REQB14443A": {"code": 'B0', "desc": "ISO14443A Anticollision REQB"},
        "WUPB14443A": {"code": 'B1', "desc": "ISO14443A Anticollision WUPB"},

        "AGCSEL":  {"code": 'F0', "desc": "AGC selection"},
        "AMPMSEL": {"code": 'F1', "desc": "AM/PM input selection"},
        "SETLED2": {"code": 'FB', "desc": "Set Led 2"},
        "SETLED3": {"code": 'F9', "desc": "Set Led 3"},
        "SETLED4": {"code": 'F7', "desc": "Set Led 4"},
        "SETLED5": {"code": 'F5', "desc": "Set Led 5"},
        "SETLED6": {"code": 'F3', "desc": "Set Led 6"},
        "CLRLED2": {"code": 'FC', "desc": "Clear Led 2"},
        "CLRLED3": {"code": 'FA', "desc": "Clear Led 3"},
        "CLRLED4": {"code": 'F8', "desc": "Clear Led 4"},
        "CLRLED5": {"code": 'F6', "desc": "Clear Led 5"},
        "CLRLED6": {"code": 'F4', "desc": "Clear Led 6"},
        "VERSION": {"code": 'FE', "desc": "Get firmware version"},
        "INITIALIZE": {"code": 'FF', "desc": "Initialize reader"},
}

NTAG5_CMD = {
        "INVENTORY":                {"code": 0x01, "desc": "Inventory"},
        "QUIET":                    {"code": 0x02, "desc": "Stay Quiet"},
        "READ_SINGLE_BLOCK":        {"code": 0x20, "desc": "Read Single Block"},
        "WRITE_SINGLE_BLOCK":       {"code": 0x21, "desc": "Write Single Block"},
        "LOCK_BLOCK":               {"code": 0x22, "desc": "Lock Block"},
        "READ_MULTIPLE_BLOCK":      {"code": 0x23, "desc": "Read Multiple Block"},
        "SELECT":                   {"code": 0x25, "desc": "Select"},
        "RESET_TO_READY":           {"code": 0x26, "desc": "Reset to Ready"},
        "WRITE_AFI":                {"code": 0x27, "desc": "Write AFI"},
        "LOCK_AFI":                 {"code": 0x28, "desc": "Lock AFI"},
        "WRITE_DSFID":              {"code": 0x29, "desc": "Write DSFID"},
        "LOCK_DSFID":               {"code": 0x2A, "desc": "Lock DSFID"},
        "GET_SYS_INFO":             {"code": 0x2B, "desc": "Get System Info"},
        "GET_MULT_BLOC_SEC_INFO":   {"code": 0x2C, "desc": "Get Multiple Block Security Status"},

        "READ_CONF":                {"code": 0xC0, "desc": "Read Configuration"},
        "WRITE_CONF":               {"code": 0xC1, "desc": "Write Configuration"},
        "READ_SRAM":                {"code": 0xD2, "desc": "Read SRAM"},
        "WRITE_SRAM":               {"code": 0xD3, "desc": "Write SRAM"},
        }

NTAG5_ADDR = {
        "SRAM_START":     {"address": 0x00},
        "SRAM_END":       {"address": 0x3F},
        "SRAM_CONF_PROT": {"address": 0x3F},
        "STATUS_REG":     {"address": 0xA0},
        "CONFIG_REG":     {"address": 0xA1},
        "EH_CONFIG_REG":  {"address": 0xA7},
        "ED_CONFIG_REG":  {"address": 0xA8},
        }

NTAG5_REGISTERS = {
        "STATUS_REG_0":    {"byte": 0x00, "SRAM_DATA_RDY_mask":   0b00100000},
        "STATUS_REG_1":    {"byte": 0x01, "I2C_IF_LOCKED_mask":   0b00000010, "NFC_IF_LOCKED_mask": 0b00000001},
        "CONFIG_REG_0":    {"byte": 0x00},
        "CONFIG_REG_1":    {"byte": 0x01, "PT_TRANSFER_DIR_mask": 0b00000001},
        "ED_CONFIG_REG":   {"byte": 0x00, "ED_CONFIG_mask":       0b00001111},
        }

def flagsbyte(double_sub_carrier=False, high_data_rate=False, inventory=False,
              protocol_extension=False, afi=False, single_slot=False,
              option=False, select=False, address=False):
    # Method to construct the flags byte
    # Reference: TI TRF9770A Evaluation Module (EVM) User's Guide, p. 8
    #            <http://www.ti.com/litv/pdf/slou321a>
    bits = '0'                                  # bit 8 (RFU) is always zero
    bits += '1' if option else '0'              # bit 7
    if inventory:
        bits += '1' if single_slot else '0'     # bit 6
        bits += '1' if afi else '0'             # bit 5
    else:
        bits += '1' if address else '0'         # bit 6
        bits += '1' if select else '0'          # bit 5
    bits += '1' if protocol_extension else '0'  # bit 4
    bits += '1' if inventory else '0'           # bit 3
    bits += '1' if high_data_rate else '0'      # bit 2
    bits += '1' if double_sub_carrier else '0'  # bit 1
    return '%02X' % int(bits, 2)     # return hex byte

class NtagInterface(PyDlpRfid2):
  app_state = None

  def __init__(self):
    self.app_state="state_initialization"
    super().__init__(serial_port="/dev/ttyUSB0", loglevel=logging.INFO)

  def get_register_byte(self, response, register):
    data = response[2:]
    byte_length = 2
    if 0 <= register < len(data) // byte_length:
      return data[register * byte_length : (register + 1) * byte_length]
    else:
      self.logger.error("invalid register index")
      return None

  #low level interface methods:
  def get_register_block(self, register):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_CONF"]["code"],
                                # data = f"{}{'00'}")
                                data = f"{register:02X}{'00'}")
    if len(response) > 0:
      return response[0]
    else:
      return '00'

  def get_status_register_block(self):
    return self.get_register_block(NTAG5_ADDR['STATUS_REG']['address'])

  def get_config_register_block(self):
    return self.get_register_block(NTAG5_ADDR['CONFIG_REG']['address'])

  def get_ed_config_register_block(self):
    return self.get_register_block(NTAG5_ADDR['ED_CONFIG_REG']['address'])

  def get_eh_config_register_block(self):
    return self.get_register_block(NTAG5_ADDR['EH_CONFIG_REG']['address'])

  def get_sram_protection_config_block(self):
    return self.get_register_block(NTAG5_ADDR['SRAM_CONF_PROT']['address'])

  def read_sram(self):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{NTAG5_ADDR['SRAM_START']['address']:02X}{'15'}")
    print(f"\n{bytes.fromhex(response[0]).decode('utf-8')}")
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{(0x15+NTAG5_ADDR['SRAM_START']['address']):02X}{'15'}")
    print(bytes.fromhex(response[0]).decode('utf-8'))
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{0x2A+NTAG5_ADDR['SRAM_START']['address']:02X}{'15'}")
    print(bytes.fromhex(response[0]).decode('utf-8'))

  def write_sram(self, string):
    hex_string = string.encode().hex()
    formatted_data = hex_string.ljust(512, '0')
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["WRITE_SRAM"]["code"],
                                # data = f"{NTAG5_ADDR['SRAM_START']['address']:02X}{'3F'}{formatted_data.upper()}")
                                data = f"{NTAG5_ADDR['SRAM_START']['address']:02X}{'01'}{'3030303031313131'}")
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["WRITE_SRAM"]["code"],
                                # data = f"{NTAG5_ADDR['SRAM_START']['address']:02X}{'3F'}{formatted_data.upper()}")
                                data = f"{NTAG5_ADDR['SRAM_END']['address']:02X}{'00'}{'46464646'}")
    self.read_sram()
    
  def select(self):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(address=True),
                                command_code=NTAG5_CMD["SELECT"]["code"],
                                data='0011ABF6580104E0')
    if len(response) > 0 and response[0] == '00':
      self.logger.info("Successfully selected NTAG5")
    else:
      self.logger.error("Failed to select NTAG5")
  
  #high level interface methods:
  def configure_energyharvesting(self):
    print("#todo")

  def get_data_direction(self):
    status_reg_block = self.get_status_register_block()
    config_reg_block = self.get_config_register_block()
    ed_config_reg_block = self.get_ed_config_register_block()
    status_1_reg_byte = int(self.get_register_byte(status_reg_block, NTAG5_REGISTERS["STATUS_REG_1"]["byte"]), 16)
    config_1_reg_byte = int(self.get_register_byte(status_reg_block, NTAG5_REGISTERS["CONFIG_REG_1"]["byte"]), 16)
    ed_config_reg_byte = int(self.get_register_byte(ed_config_reg_block, NTAG5_REGISTERS["ED_CONFIG_REG"]["byte"]), 16)
    if status_1_reg_byte & NTAG5_REGISTERS["STATUS_REG_1"]["I2C_IF_LOCKED_mask"] == 0x1 and config_1_reg_byte & NTAG5_REGISTERS["CONFIG_REG_1"]["PT_TRANSFER_DIR_mask"] == 0x0 and ed_config_reg_byte & NTAG5_REGISTERS["ED_CONFIG_REG"]["ED_CONFIG_mask"] == 0x3:
      return "I2C_NFC"
    if status_1_reg_byte & NTAG5_REGISTERS["STATUS_REG_1"]["NFC_IF_LOCKED_mask"] == 0x1 and config_1_reg_byte & NTAG5_REGISTERS["CONFIG_REG_1"]["PT_TRANSFER_DIR_mask"] == 0x1 and ed_config_reg_byte & NTAG5_REGISTERS["ED_CONFIG_REG"]["ED_CONFIG_mask"] == 0x4:
      return "NFC_I2C"
    self.logger.error("invalid ntag configuration")
    return "INVALID_SETTINGS"


  def get_sram_data_ready(self):
    status_reg_block = self.get_status_register_block()
    status_0_reg_byte = self.get_register_byte(status_reg_block, NTAG5_REGISTERS["STATUS_REG_0"]["byte"])
    return int(status_0_reg_byte, 16) & NTAG5_REGISTERS["STATUS_REG_0"]["SRAM_DATA_RDY_mask"]

  def initialize_connection(self):
    self.init_kit()
    self.enable_internal_antenna()
    self.set_protocol()
    self.inventory()
    self.select()
  
  #state machine methods:
  def state_init(self):
    self.initialize_connection()
    self.app_state = "state_i2c_nfc_direction"

  def state_i2c_nfc_dir(self):
    print("..................running state i2c->nfc", end='\r')
    if self.get_sram_data_ready():
      message = self.read_sram()
      if self.get_sram_data_ready():
        print(f"...... failed to read SRAM, trying again", end='\r') 
      else:
        self.app_state = "state_nfc_i2c_direction"
    else:
      print("...........waiting for mcu to write sram", end='\r')
            
  def state_nfc_i2c_dir(self):
    print("..................running state nfc->i2c", end='\r')
    if self.get_data_direction() == "NFC_I2C":
      self.write_sram("This data is sent from nfc reader")
      self.app_state = "state_i2c_nfc_direction"
    else:
      print("waiting for mcu to switch data direction", end='\r')


  def default_state(self):
    self.logger.error("unexpteced state, error")
    sys.exit(0)

  state_machine = {
    "state_initialization":    state_init,
    "state_i2c_nfc_direction": state_i2c_nfc_dir,
    "state_nfc_i2c_direction": state_nfc_i2c_dir,
    "state_default":           default_state
  }

def start_application(argv):
    ntag = NtagInterface()

    while True:
      state_method = ntag.state_machine.get(ntag.app_state, ntag.default_state)(ntag)
      time.sleep(0.5)

if __name__ == "__main__":
    start_application(sys.argv[1:])
    