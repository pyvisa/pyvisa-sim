# -*- coding: utf-8 -*-
"""Simulated backend for PyVISA.

:copyright: 2014-2024 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""

from importlib.metadata import PackageNotFoundError, version

from .highlevel import SimVisaLibrary

__version__ = "unknown"
try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


WRAPPER_CLASS = SimVisaLibrary
