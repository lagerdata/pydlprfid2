#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

from setuptools import setup

setup(
    name='pydlprfid2',
    version='0.1',

    description='Drive DLP RFID2 reader to read/write EEPROM',
    long_description='pyrfidgeek fork that drive DLP RFID2 reader to read/write EEPROM',
    url='https://github.com/Martoni/pydlprfid2',
    author='Fabien Marteau',
    author_email='fabien.marteau@armadeus.com',
    license='MIT',
    keywords='rfid iso15693 iso14443 libdev trf7970a dlprfid2',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],

    packages=['pydlprfid2'],
    scripts=['bin/pdr2'],

    # Run-time dependencies
    install_requires=['pyserial'],

    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-pep8']
)
