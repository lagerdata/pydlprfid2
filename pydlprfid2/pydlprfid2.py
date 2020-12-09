# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

import re
import time
import serial
import pprint
import logging
import binascii

try:
    # Use colored logging if termcolor is available
    from termcolor import colored
except ImportError:
    # But just pass through the message if not
    def colored(msg, *args, **kwargs):
        return msg

class StandardError(Exception):
    pass

ISO15693 = 'ISO15693'
ISO14443A = 'ISO14443A'
ISO14443B = 'ISO14443B'

# sloa157.pdf Table 4 «HOST (PC GUI to MCU)» page 18
DLP_CMD = {
        "DIRECTMODE": {"code": '0F', "desc": "Direct mode"},
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


# commands codes from datasheet m24lr64e-r.pdf page 78
M24LR64ER_CMD = {
        "INVENTORY":           {"code": 0x01, "desc": "Inventory"},
        "QUIET":               {"code": 0x02, "desc": "Stay Quiet"},
        "SET_READ_MODE_USER":  {"code": 0x10, "desc": "Set Read Mode to User Memory"},
        "READ_SINGLE_BLOCK":   {"code": 0x20, "desc": "Read Single Block"},
        "WRITE_SINGLE_BLOCK":  {"code": 0x21, "desc": "Write Single Block"},
        "READ_MULTIPLE_BLOCK": {"code": 0x23, "desc": "Read Multiple Block"},
        "SELECT":              {"code": 0x25, "desc": "Select"},
        "RESET_TO_READY":      {"code": 0x26, "desc": "Reset to Ready"},
        "WRITE_AFI":           {"code": 0x27, "desc": "Write AFI"},
        "LOCK_AFI":            {"code": 0x28, "desc": "Lock AFI"},
        "WRITE_DSFID":         {"code": 0x29, "desc": "Write DSFID"},
        "LOCK_DSFID":          {"code": 0x2A, "desc": "Lock DSFID"},
        "GET_SYS_INFO":        {"code": 0x2B, "desc": "Get System Info"},

        "GET_MULT_BLOC_SEC_INFO":{"code": 0x2C, "desc": "Get Multiple Block Security Status"},
        "WRITE_SECT_PSWD":   {"code": 0xB1, "desc": "Write-sector Password"},
        "LOCK_SECT_PSWD":    {"code": 0xB2, "desc": "Lock-sector"},
        "PRESENT_SECT_PSWD": {"code": 0xB3, "desc": "Present-sector Password"},
        "FAST_READ_SINGLE_BLOCK": {"code": 0xC0, "desc": "Fast Read Single Block"},
        "FAST_INVENTORY_INIT":    {"code": 0xC1, "desc": "Fast Inventory Initiated"},
        "FAST_INIT":              {"code": 0xC2, "desc": "Fast Initiate"},
        "FAST_READ_MULT_BLOCK":   {"code": 0xC3, "desc": "Fast Read Multiple Block"},
        "INVENTORY_INIT":         {"code": 0xD1, "desc": "Inventory Initiated"},
        "INITIATE":               {"code": 0xD2, "desc": "Initiate"},
        "READCFG": {"code": 0xA0, "desc": "ReadCfg"},
        "WRITEEHCFG": {"code": 0xA1, "desc": "WriteEHCfg"},
        "SETRSTEHEN": {"code": 0xA2, "desc": "SetRstEHEn"},
        "CHECKEHEN" : {"code": 0xA3, "desc": "CheckEHEn"},
        "WRITEDOCFG": {"code": 0xA4, "desc": "WriteDOCfg"}
        }

def reverse_uid(uid):
    if len(uid) != 16:
        raise Exception(f"Wrong uid size {len(uid)}, should be 16")
    return (uid[-2:] +
            uid[-4:-2] +
            uid[-6:-4] +
            uid[-8:-6] +
            uid[-10:-8] +
            uid[-12:-10] +
            uid[-14:-12] +
            uid[-16:-14])

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


class PyDlpRfid2(object):
    BAUDRATE=115200
    STOP_BITS=serial.STOPBITS_ONE
    PARITY=serial.PARITY_NONE
    BYTESIZE=serial.EIGHTBITS

    def __init__(self, serial_port, loglevel=logging.INFO):
        self.protocol = None
        self.__log_config(loglevel)
        self.sp = serial.Serial(port=serial_port,
                                baudrate=self.BAUDRATE,
                                stopbits=self.STOP_BITS,
                                parity=self.PARITY,
                                bytesize=self.BYTESIZE,
                                timeout=0.1)

        if not self.sp:
            raise StandardError('Could not connect to serial port ' + serial_port)

        self.logger.debug('Connected to ' + self.sp.portstr)
        self.flush()

    def __log_config(self, loglevel):
        self.logger = logging.getLogger(__name__)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(loglevel)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(ch)
        self.logger.setLevel(loglevel)


    def enable_external_antenna(self):
        cmdstr = DLP_CMD["EXTERNANT"]["code"]
        self.issue_evm_command(cmd=cmdstr)

    def enable_internal_antenna(self):
        cmdstr = DLP_CMD["INTERNANT"]["code"]
        self.issue_evm_command(cmd=cmdstr)

    def init_kit(self):
        initcmd = DLP_CMD["INITIALIZE"]["code"]
        self.issue_evm_command(cmd=initcmd)  # Should return "TRF7970A EVM"

    def debug_test(self):
        print("DEBUG TEST:")
        print("init (ping)")
        self.init_kit()
        print("enable internal antenna")
        self.enable_internal_antenna()
        print("enable external antenna")
        self.enable_external_antenna()
        print("Read UID from a Single ISO15693 Tag (Single-Slot Inventory):")
        print(" Set ISO15693 Mode:")
        self.set_iso15693()
        print("AGC Toggle:")
        self.issue_evm_command(cmd=DLP_CMD["AGCSEL"]["code"], prms='00')
        print("AM/PM Toggle:")
        self.issue_evm_command(cmd=DLP_CMD['AMPMSEL']["code"], prms='FF')
        print("Single-Slot Inventory Request :")
        self.inventory_iso15693(single_slot=True)
        print("Read a Block from a Texas Instruments ISO15693 Tag:")
        print(" Set Read Mode to User Memory:")
        self.issue_iso15693_command(cmd=DLP_CMD["WRITESINGLE"]["code"],
                                    flags=flagsbyte(),
                                    command_code='%02X'%M24LR64ER_CMD["WRITE_SINGLE_BLOCK"]["code"],
                                    data='0100')
        print("AGC Toggle:")
        self.issue_evm_command(cmd=DLP_CMD["AGCSEL"]["code"], prms='00')
        print("AM/PM Toggle:")
        self.issue_evm_command(cmd=DLP_CMD['AMPMSEL']["code"], prms='FF')

        print("Read Block 4:")
        self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                   flags=flagsbyte(),
                                   command_code='%02X'%M24LR64ER_CMD["READ_SINGLE_BLOCK"]["code"],
                                   data='%02X' % (4))
        print("Turn RF Carrier Off:")
        self.issue_iso15693_command(cmd=DLP_CMD["WRITESINGLE"]["code"],
                                    flags=flagsbyte(),
                                    command_code='%02X'%M24LR64ER_CMD["INVENTORY"]["code"],
                                    data='')
        print("TODO")
        print("")
        print("End of debug")

    def set_iso15693(self):
        # Select protocol: 15693 with full power
        self.issue_evm_command(cmd=DLP_CMD["WRITESINGLE"]["code"],
                               prms='00210100')

    def set_protocol(self, protocol=ISO15693):

        self.protocol = protocol

        # 1. Initialize reader: 0xFF
        # 0108000304 FF 0000
        initcmd = DLP_CMD["INITIALIZE"]["code"]
        self.issue_evm_command(cmd=initcmd)  # Should return "TRF7970A EVM"

        # self.issue_evm_command(cmd='10', prms='0121')
        # self.issue_evm_command(cmd='10', prms='0021')

        # Select protocol: 15693 with full power
        self.issue_evm_command(cmd=DLP_CMD["WRITESINGLE"]["code"],
                               prms='00210100')

        # Setting up registers:
        #   0x00 Chip Status Control: Set to 0x21 for full power, 0x31 for half power
        #   0x01 ISO Control: Set to 0x00 for ISO15693, 0x09 for ISO14443A, 0x0C for ISO14443B
        protocol_values = {
            ISO15693: '00',   # 01 for 1-out-of-256 modulation
            ISO14443A: '09',
            ISO14443B: '0C',
        }
        self.issue_evm_command(cmd=DLP_CMD["WRITESINGLE"]["code"],
                               prms='0021' + '01' + protocol_values[protocol])

        # 3. AGC selection (0xF0) : AGC enable (0x00)
        # 0109000304 F0 00 0000
        self.issue_evm_command(cmd=DLP_CMD["AGCSEL"]["code"], prms='00')

        # 4. AM/PM input selection (0xF1) : AM input (0xFF)
        # 0109000304 F1 FF 0000
        self.issue_evm_command(cmd=DLP_CMD['AMPMSEL']["code"], prms='FF')

    def enable_led(self, led_no):
        cmd_codes = {2: 'FB', 3: 'F9', 4: 'F7', 5: 'F5', 6: 'F3'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def disable_led(self, led_no):
        cmd_codes = {2: 'FC', 3: 'FA', 4: 'F8', 5: 'F6', 6: 'F4'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def inventory(self, **kwargs):
        if self.protocol == ISO15693:
            return self.inventory_iso15693(**kwargs)
        elif self.protocol == ISO14443A:
            return self.inventory_iso14443A(**kwargs)


    def inventory_iso14443A(self):
        """
        By sending a 0xA0 command to the EVM module, the module will carry out
        the whole ISO14443 anti-collision procedure and return the tags found.

            >>> Req type A (0x26)
            <<< ATQA (0x04 0x00)
            >>> Select all (0x93, 0x20)
            <<< UID + BCC

        """
        response = self.issue_evm_command(cmd=DLP_CMD["REQA14443A"]["code"])

        for itm in response:
            iba = bytearray.fromhex(itm)
            # Assume 4-byte UID + 1 byte Block Check Character (BCC)
            if len(iba) != 5:
                self.logger.warn('Encountered tag with UID of unknown length')
                continue
            if iba[0] ^ iba[1] ^ iba[2] ^ iba[3] ^ iba[4] != 0:
                self.logger.warn('BCC check failed for tag')
                continue
            uid = itm[:8]  # hex string, so each byte is two chars

            self.logger.debug('Found tag: %s (%s) ', uid, itm[8:])
            return uid

            # See https://github.com/nfc-tools/libnfc/blob/master/examples/nfc-anticol.c

    def inventory_iso15693(self, single_slot=False):
        # Command code 0x01: ISO 15693 Inventory request
        # Example: 010B000304 14 24 0100 0000
        response = self.issue_iso15693_command(cmd=DLP_CMD["ANTICOL15693"]["code"],
                                               flags=flagsbyte(inventory=True,
                                                               single_slot=single_slot),
                                               command_code='%02X'%M24LR64ER_CMD["INVENTORY"]["code"],
                                               data='00')
        for itm in response:
            itm = itm.split(',')
            if itm[0] == 'z':
                self.logger.debug('Tag conflict!')
            else:
                if len(itm[0]) == 16:
                    uid = itm[0]
                    rssi = itm[1]
                    self.logger.debug('Found tag: %s (%s) ', uid, rssi)
                    return reverse_uid(uid), rssi

    def get_dlp_rfid2_firmware_version(self):
        response = self.issue_evm_command(DLP_CMD["VERSION"]["code"], get_full_response=True)
        return response


    def eeprom_get_system_info(self, uid=None):
        if uid is None:
            response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(),
                                command_code='%02X'%M24LR64ER_CMD["GET_SYS_INFO"]["code"])
        else:
            response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                flags=flagsbyte(address=True),
                                command_code='%02X'%M24LR64ER_CMD["GET_SYS_INFO"]["code"],
                                data=reverse_uid(uid))
        if len(response) == 1 and response[0] != '':
            return response[0]
        else:
            return None


    def eeprom_read_single_block(self, uid, blockoffset):
        address = False
        data='%02X%02X' % (blockoffset&0xFF, (blockoffset>>8)&0xFF)
        if uid is not None:
            data = reverse_uid(uid) + data
            address = True
        response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                           flags=flagsbyte(address=address, protocol_extension=True),
                           command_code='%02X'%M24LR64ER_CMD["READ_SINGLE_BLOCK"]["code"],
                           data=data)
        if len(response) == 1 and response[0] != '':
            resp = response[0]
            if resp[0:2] == '00':
                return resp[2:10]
            else:
                raise StandardError("Wrong code return {} ({})".format(resp[0:2], resp))
        else:
            return None

    def eeprom_read_multiple_block(self, uid, blocknum, blockoffset):
        address = False
        if blocknum < 1:
            raise Exception("Blocknum can't be 0 or less")
        data='%02X%02X%02X' % (blockoffset&0xff, (blockoffset>>8)&0xff, blocknum-1)
        if uid is not None:
            address = True
            data = reverse_uid(uid) + data
        response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                    flags=flagsbyte(address=address, protocol_extension=True),
                    command_code='%02X'%M24LR64ER_CMD["READ_MULTIPLE_BLOCK"]["code"],
                    data=data)
        if len(response) == 1 and response[0] != '':
            resp = response[0]
            if resp[0:2] == '00':
                return resp[2:]
            else:
                raise StandardError("Wrong code return {} ({})".format(resp[0:2], resp))
        else:
            return None

    def eeprom_write_single_block(self, uid, block_offset, datastr, readback=True):
        address = False
        if len(datastr) > 8:
            raise StandardError("Data too long")
        try:
            datavalue = "{:08X}".format(int(datastr, 16))
        except ValueError:
            raise StandardError("Data is not correct hexadecimal value")

        data = "%02X%02X" % (block_offset&0xff, (block_offset>>8)&0xff) + datavalue
        if uid is not None:
            address = True
            data = reverse_uid(uid) + data

        response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                 flags=flagsbyte(address=address, protocol_extension=True),
                 command_code='%02X'%M24LR64ER_CMD["WRITE_SINGLE_BLOCK"]["code"],
                 data=data)
        if readback:
            block_value = self.eeprom_read_single_block(uid, block_offset)
            if block_value != datastr:
                raise Exception("Write error on block {}: read {} instead of {}"
                        .format(block_offset, block_value, datastr))
        if len(response) == 1 and response[0] != '':
            return response[0]
        else:
            return None

    def eeprom_write_multiple_block(self, uid, block_offset, datalist):
        offset = block_offset
        resplist = []
        for data in datalist:
            resp = self.eeprom_write_single_block(uid, offset, "{:08X}".format(data))
            offset = offset + 1
            if resp is None:
                raise StandardError("Writing error on data {:08X}".format(data))
            resplist.append(resp)
        return resplist

    def write_blocks_to_card(self, uid, data_bytes, offset=0, nblocks=8):
        for x in range(offset, nblocks):
            success = False
            attempts = 0
            max_attempts = 10
            while not success:
                attempts += 1
                success = self.write_block(uid, x, data_bytes[x*4:x*4+4])
                if not success:
                    self.logger.warn('Write failed, retrying')
                    if attempts > max_attempts:
                        self.logger.warn('Giving up!')
                        return False
                    # time.sleep(1.0)
        return True

    def erase_card(self, uid):
        data_bytes = ['00' for x in range(32)]
        return self.write_blocks_to_card(uid, data_bytes)

    def write_block(self, uid, block_number, data):
        if type(data) != list or len(data) != 4:
            raise StandardError('write_block got data of unknown type/length')

        response = self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                               flags=flagsbyte(address=True),  # 32 (dec) <-> 20 (hex)
                                               command_code='%02X'%M24LR64ER_CMD["WRITE_SINGLE_BLOCK"]["code"],
                                               data='%s%02X%s' % (uid, block_number, ''.join(data)))
        if response[0] == '00':
            self.logger.debug('Wrote block %d successfully', block_number)
            return True
        else:
            return False

    def unlock_afi(self, uid):
        self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                    flags=flagsbyte(address=False,
                                                    high_data_rate=True,
                                                    option=False),  # 32 (dec) <-> 20 (hex)
                                    command_code='%02X'%M24LR64ER_CMD["WRITE_AFI"]["code"],
                                    data='C2')

    def lock_afi(self, uid):
        self.issue_iso15693_command(cmd=DLP_CMD["REQUESTCMD"]["code"],
                                    flags=flagsbyte(address=False,
                                                    high_data_rate=False,
                                                    option=False),  # 32 (dec) <-> 20 (hex)
                                    command_code='%02X'%M24LR64ER_CMD["WRITE_AFI"]["code"],
                                    data='07')

    def issue_evm_command(self, cmd, prms='', get_full_response=False):
        # The EVM protocol has a general form as shown below:
        #  1. SOF (Start of File): 0x01
        #  2. LENGTH : Two bytes define the number of bytes in the frame including SOF. Least Significant Byte first!
        #  3. READER_TYPE : 0x03
        #  4. ENTITY : 0x04
        #  5. CMD : The command
        #  6. PRMS : Parameters
        #  7. EOF : 0x0000

        # Two-digit hex strings (without 0x prefix)
        sof = '01'
        reader_type = '03'
        entity = '04'
        eof = '0000'

        result = reader_type + entity + cmd + prms + eof

        length = int(len(result)/2) + 3  # Number of *bytes*, + 3 to include SOF and LENGTH
        length = '%04X' % length  # Convert int to hex
        length = binascii.unhexlify(length)[::-1]  # Reverse hex string to get LSB first
        length = binascii.hexlify(length).decode('ascii')

        result = sof + length + result
        self.write(result.upper())
        response = self.read()
        if get_full_response:
            return response
        else:
            return self.get_response(response)

    def issue_iso15693_command(self, cmd, flags='', command_code='', data=''):
        return self.issue_evm_command(cmd, flags + command_code + data)

    def flush(self):
        self.sp.readall()

    def write(self, msg):
        self.logger.debug('SEND%3d: ' % (len(msg)/2) +
                          msg[0:2] +
                          colored(msg[2:4], 'yellow') +
                          msg[4:10] +
                          colored(msg[10:12], 'red') +
                          msg[12:-4] +
                          colored(msg[-4:], 'green'))
        self.sp.write(msg.encode('ascii'))

    def read(self):
        msg = self.sp.readall()
        self.logger.debug('RETR%3d: ' % (len(msg)/2) + colored(pprint.saferepr(msg).strip("'"), 'cyan'))
        return msg

    def get_response(self, response):
        return re.findall(r'\[(.*?)\]', response.decode('ascii'))

    def close(self):
        self.sp.close()
