**pyDlpRfid2** is a fork from [**PyRFIDGeek**](https://github.com/scriptotek/pyrfidgeek)
that drive [DLP-RFID2](https://www.dlpdesign.com/rf/rfid2.php) module
([TRF7970A](http://www.ti.com/product/TRF7970A) chipset) to read/write EEPROM-RFID.

# Install

pyDlpRfid2 is a standard distutil package, to install it simply clone this
repository :

    $ git clone https://github.com/Martoni/pydlprfid2.git
    $ cd pydlprfid2/

Then install it with pip :

    $ python -m pip install -e .
    
# shell commands

The distribution contain a binary script named **pdr2** that can be used as standard shell command:

    $  pdr2 -h
    Usages:
    pdr2 [options]
    -h, --help               print this help
    -d, --devtty filename    uart dev name path
    -p, --protocol PROTOCOL  default ISO15693
    -l, --listtag            list tag present
    
A second binary come with this package to convert BusPirate to a standard USB-UART adapter. If you are using buspirate (v4) with your DLP-RFID2 module, you will have to launch this command before:

    $  bp2bridge -d/dev/ttyACM0
    /dev/ttyACM0 is now configured as standard tty uart (115200)

# Module import

TODO

# EEPROM access

TODO
