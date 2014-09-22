# -*- coding: utf-8 -*-
"""
    pyvisa-sim
    ~~~~~~~~~~

    Simulated backend for PyVISA.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

from __future__ import division, unicode_literals, print_function, absolute_import

from .highlevel import SimVisaLibrary

WRAPPER_CLASS = SimVisaLibrary

