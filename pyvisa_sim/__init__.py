# -*- coding: utf-8 -*-
"""
    pyvisa-sim
    ~~~~~~~~~~

    Simulated backend for PyVISA.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
import pkg_resources

from .highlevel import SimVisaLibrary


__version__ = "unknown"
try:  # pragma: no cover
    __version__ = pkg_resources.get_distribution("pyvisa-sim").version
except:  # pragma: no cover
    pass  # we seem to have a local copy without any repository control or installed without setuptools
    # so the reported version will be __unknown__


WRAPPER_CLASS = SimVisaLibrary
