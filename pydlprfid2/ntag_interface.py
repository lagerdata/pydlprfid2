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
        }

NTAG5_CONFIG = {
        "SRAM_PROT_CONFIG":   {"address": 0x3F, "byte": 0x01},
        "EH_CONFIG":          {"address": 0x3D, "byte": 0x00},
        "ED_CONFIG":          {"address": 0x3D, "byte": 0x02},
        "DEVICE_SEC_CONFIG":  {"address": 0x3F, "byte": 0x00},
        }

NTAG5_REGISTERS = {
        "STATUS_0_REG":   {"address": 0xA0, "byte": 0x00, "SRAM_DATA_RDY_mask": 0b00100000},
        "STATUS_1_REG":   {"address": 0xA0, "byte": 0x01, "I2C_IF_LOCKED_mask": 0b00000010, "NFC_IF_LOCKED_mask": 0b00000001},
        "CONFIG_0_REG":   {"address": 0xA1, "byte": 0x00},
        "CONFIG_1_REG":   {"address": 0xA1, "byte": 0x01,  "PT_TRANSFER_DIR_mask": 0b00000001, "SRAM_ENABLED_mask": 0b00000010},
        "EH_CONFIG_REG":  {"address": 0xA7, "byte": 0x00, "EH_LOAD_OK_mask": 0b10000000, "EH_TRIGGER_mask": 0b00001000, "EH_ENABLE": 0b00000001},
        "ED_CONFIG_REG":  {"address": 0xA8, "byte": 0x00, "ED_CONFIG_mask": 0b00001111},
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
    super().__init__(serial_port="/dev/ttyUSB0", loglevel=logging.DEBUG)

  #low level interface methods:
  def get_memory_block(self, address):
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_CONF"]["code"],
                                data = f"{address:02X}{'00'}")
    if len(response) > 0 and len(response[0]) > 1:
      data = response[0][2:]
      return data[:8]
    else:
      self.logger.error("failed to get memory block")
      return None

  def get_memory_byte(self, address, byte):
    response = self.get_memory_block(address)
    if response != None:
      if 0x0 <= byte <= 0x3:
        return response[byte * 2 : (byte * 2) + 2]
      else:
        self.logger.error("invalid byte index")
        return None
    else:
      return None

  def get_register_bit(self, register, bit_mask):
    register_byte  = self.get_memory_byte(NTAG5_REGISTERS[register]["address"], NTAG5_REGISTERS[register]["byte"])
    if register_byte != None:
      return int(register_byte, 16) & NTAG5_REGISTERS[register][bit_mask]
    else:
      return None

  def get_config_bit(self, config, bit_mask):
    config_byte  = self.get_memory_byte(NTAG5_CONFIG[config]["address"], NTAG5_CONFIG[config]["byte"])
    if config_byte != None:
      return int(config_byte, 16) & NTAG5_CONFIG[config][bit_mask]
    else:
      return None

  def set_memory_block(self, address, value):
    value_string = f"{value:08X}"
    data_bytes = [value_string[i:i+2] for i in range(0, len(value_string), 2)]
    data_bytes.reverse()
    data_inverse = ''.join(data_bytes)
    response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["WRITE_CONF"]["code"],
                                data = f"{address:02X}{data_inverse}")
    if not (len(response) > 0):
      self.logger.error("failed to set memory block")

  # def set_memory_byte(address, byte, value):
  #   # current_block_value = self.get_memory_block(address)
  #   # if current_block_value != None:
  #   #   block_bytes = bytearray(current_block_value)
  #   #   block_bytes[byte] = value
  #   #   new_block_value = byte_data.hex()
  #   #   self.set_memory_block(address, new_block_value)
  #   # else:
  #   #   self.logger.error("failed to get memory")

  # def set_memory_bit(address, byte, bite, value):
  #   # todo

  def read_sram(self):
    response_1 = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{NTAG5_ADDR['SRAM_START']['address']:02X}{'15'}")
    response_2 = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{(0x15+NTAG5_ADDR['SRAM_START']['address']):02X}{'15'}")
    response_3 = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code=NTAG5_CMD["READ_SRAM"]["code"],
                                data = f"{0x2A+NTAG5_ADDR['SRAM_START']['address']:02X}{'15'}")
    if len(reponse_1) > 0 and len(reponse_2) > 0  and len(reponse_3) > 0:
      print(f"\n{bytes.fromhex(response_1[0]).decode('utf-8')}")
      print(bytes.fromhex(response_2[0]).decode("utf-8"))
      print(bytes.fromhex(response_3[0]).decode("utf-8"))
    else:
      print("error reading sram")

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

  def discover(self):
    response = self.inventory()
    try:
      if len(response) > 0:
        self.logger.info(f"Discovered NFC tag with uuid {response[0]}")
        return response[0]
    except:
      self.logger.error("No tag found in RF field")
      return None

  def select(self, tag_uuid):
    if tag_uuid != None:
      response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                  flags=flagsbyte(address=True),
                                  command_code=NTAG5_CMD["SELECT"]["code"],
                                  data=tag_uuid)
      if len(response) > 0 and response[0] == '00':
        self.logger.info("Successfully selected NTAG5")
        return "NTAG5_SELECTED"
      else:
        self.logger.error("Failed to select NTAG5")
        return None

  #high level interface methods:
  def configure_energyharvesting(self):
    # print(f"00: {self.get_memory_block(NTAG5_CONFIG['EH_CONFIG']['address'])}")
    # self.set_memory_block(NTAG5_CONFIG['EH_CONFIG']['address'], 0x8)
    if self.get_register_bit('EH_CONFIG_REG', 'EH_LOAD_OK_mask'):
      print("EH_LOAD_OK, triggering energy harvesting")
      #set stuff
      return "ENERGY_HARVEST_SET"
    else:
      print("..........................eh load not ok", end='\r')
      return None

  def get_data_direction(self):
    i2c_if_locked = self.get_register_bit("STATUS_1_REG", "I2C_IF_LOCKED_mask")
    nfc_if_locked = self.get_register_bit("STATUS_1_REG", "NFC_IF_LOCKED_mask")
    pt_xfer_dir   = self.get_register_bit("CONFIG_1_REG", "PT_TRANSFER_DIR_mask")
    ed_config     = self.get_register_bit("ED_CONFIG_REG", "ED_CONFIG_mask")
    if i2c_if_locked == 0x1 and pt_xfer_dir == 0x0 and ed_config == 0x3:
      return "I2C_NFC"
    if nfc_if_locked == 0x1 and pt_xfer_dir == 0x1 and ed_config == 0x4:
      return "NFC_I2C"
    self.logger.error("invalid ntag configuration")
    return None


  def get_sram_data_ready(self):
    return self.get_register_bit("STATUS_0_REG", "SRAM_DATA_RDY_mask")

  def initialize_connection(self):
    self.init_kit()
    self.enable_internal_antenna()
    self.set_protocol()
    tag_uuid = self.discover()
    if self.select(tag_uuid) == "NTAG5_SELECTED":
      return "INIT_OK"
    else:
      return None

  #state machine methods:
  def state_init(self):
    if self.initialize_connection() == "INIT_OK":
      self.app_state = "state_trigger_energy_harvest"
      # self.app_state = "state_i2c_nfc_direction"

  def state_trigger_eh(self):
    print("....running state trigger energy harvest", end='\r')
    if self.configure_energyharvesting() == "ENERGY_HARVEST_SET":
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
    "state_trigger_energy_harvest": state_trigger_eh,
    "state_initialization":         state_init,
    "state_i2c_nfc_direction":      state_i2c_nfc_dir,
    "state_nfc_i2c_direction":      state_nfc_i2c_dir,
    "state_default":                default_state
  }

def start_application(argv):
    ntag = NtagInterface()

    while True:
      state_method = ntag.state_machine.get(ntag.app_state, ntag.default_state)(ntag)
      time.sleep(0.5)

if __name__ == "__main__":
    start_application(sys.argv[1:])
