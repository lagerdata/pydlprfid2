**pyDlpRfid2** is a fork from [**PyRFIDGeek**](https://github.com/scriptotek/pyrfidgeek)
that drive [DLP-RFID2](https://www.dlpdesign.com/rf/rfid2.php) module
([TRF7970A](http://www.ti.com/product/TRF7970A) chipset) to read/write EEPROM-RFID [M24LR64E-R](https://www.st.com/resource/en/datasheet/m24lr64e-r.pdf).

# Install

pyDlpRfid2 is a standard distutil package, to install it simply clone this
repository :

    $ git clone https://github.com/Martoni/pydlprfid2.git
    $ cd pydlprfid2/

Then install it with pip :

    $ python -m pip install -e .
    
# shell commands

The distribution contain a binary script named **pdr2** that can be used as standard shell command:

    $ pdr2 -h
    Usages:
    pdr2 [options]
    -h, --help               print this help
    -v, --verbose            print more messages
    -d, --devtty=filename    uart dev name path
    -p, --protocol=PROTOCOL  default ISO15693
    -l, --listtag            list tag present
    -u, --uid=UID            give UID to access
    -r, --read=OFFSET        read one block (hex)
    -m, --readmultiple=NBR:OFFSET
                             read multiple blocks (hex:hex)
    -M, --writemultiple=OFFSET:[DATA0,DATA1,...]
                             write multiple blocks (hex)
    -g, --getsysinfo         read eeprom info
    -t, --test               launch debug test code
    -w, --writesingle=OFFSET:DATA
                             write data in one block


A second binary come with this package to convert BusPirate to a standard USB-UART adapter. If you are using buspirate (v4) with your DLP-RFID2 module, you will have to launch this command before:

    $  bp2bridge -d/dev/ttyACM0
    /dev/ttyACM0 is now configured as standard tty uart (115200)


# EEPROM access

## Reading

- read block 1 of eeprom with uid E0025E167B532A87 :

    $ pdr2 -d/dev/ttyACM0 -r1 -uE0025E167B532A87
    Initilize the DLP
    Block 0x01 : 012345

- read 4 block from 0 with uid E0025E167B532A87 :

    $ pdr2 -d/dev/ttyACM0 -m4:0 -uE0025E167B532A87
    Initilize the DLP
    Block 0x0000 to 0x0003 : FFFFFFFF01234567FFFFFFFFFFFFFFFF

## Writing

- write block 1 of eeprom with uid E0025E167B532A87 :

    $ pdr2 -d/dev/ttyACM0 -w2:76543210 -uE0025E167B532A87
    Initilize the DLP
    76543210 written at 2

- write 4 blocks begin at block 4 with uid E0025E167B532A87 :

    $ pdr2 -d/dev/ttyACM0 -M0:"00000000, 11111111, 22222222, AAAAAAAA, EEEEEEEE" -uE0025E167B532A87
    Initilize the DLP
    Block 0x0000 to 0x0004 written

