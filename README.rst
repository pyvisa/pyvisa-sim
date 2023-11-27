PyVISA-sim
==========

.. image:: https://github.com/pyvisa/pyvisa-sim/workflows/Continuous%20Integration/badge.svg
    :target: https://github.com/pyvisa/pyvisa-sim/actions
    :alt: Continuous integration
.. image:: https://github.com/pyvisa/pyvisa-sim/workflows/Documentation%20building/badge.svg
    :target: https://github.com/pyvisa/pyvisa/actions
    :alt: Documentation building
.. image:: https://codecov.io/gh/pyvisa/pyvisa-sim/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/pyvisa/pyvisa-sim
    :alt: Code Coverage
.. image:: https://readthedocs.org/projects/pyvisa-sim/badge/?version=latest
    :target: https://pyvisa-sim.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://img.shields.io/pypi/l/PyVISA-sim
    :target: https://pypi.python.org/pypi/pyvisa-sim
    :alt: PyPI - License
.. image:: https://img.shields.io/pypi/v/PyVISA-sim
    :target: https://pypi.python.org/pypi/pyvisa-sim
    :alt: PyPI

PyVISA-sim is a PyVISA backend that simulates a large part of the
"Virtual Instrument Software Architecture" (`VISA`_).

Description
-----------

PyVISA started as a wrapper for the NI-VISA library and therefore you
need to install the National Instruments VISA library in your system.
This works most of the time, for most people. But sometimes you need to
test PyVISA without the physical devices or even without NI-VISA.

Starting from version 1.6, PyVISA allows to use different backends.
These backends can be dynamically loaded. PyVISA-sim is one of such
backends. It implements most of the methods for Message Based
communication (Serial/USB/GPIB/Ethernet) in a simulated environment. The
behaviour of simulated devices can be controlled by a simple plain text
configuration file.

VISA and Python
---------------

Python has a couple of features that make it very interesting for
measurement controlling:

-  Python is an easy-to-learn scripting language with short development
   cycles.
-  It represents a high abstraction level, which perfectly blends with
   the abstraction level of measurement programs.
-  It has a very rich set of native libraries, including numerical and
   plotting modules for data analysis and visualisation.
-  A large set of books (in many languages) and on-line publications is
   available.

Requirements
------------

-  Python (tested with 3.8 to 3.11)
-  PyVISA 1.11+

Installation
------------

Using ``pip``:

   $ pip install -U pyvisa-sim

or install the development version:

   $ pip install git+https://github.com/pyvisa/pyvisa-sim

PyVISA is automatically installed if needed.


Documentation
-------------

The documentation can be read online at https://pyvisa-sim.readthedocs.org

.. _VISA: http://www.ivifoundation.org/Downloads/Specifications.html
