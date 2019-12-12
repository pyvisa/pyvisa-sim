|Build Status|

PyVISA-sim
==========

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

-  Python (tested with 2.7, and 3.4 to 3.8)
-  PyVISA 1.6+

Installation
------------

Using ``pip``:

   $ pip install -U pyvisa-sim

or install the development version:

   $ pip install -U
   `https://github.com/pyvisa/pyvisa-sim/zipball/master`_

PyVISA is automatically installed if needed.


Testing
-------

Ensure you have ``tox`` installed.
Then you can simply invoke

   $ tox

to run tests for all supported Python versions, or select one with

   $ tox -e pyXY

with ``X`` being the major version (2 or 3) and ``Y`` the minor version.

Documentation
-------------

The documentation can be read online at
`https://pyvisa-sim.readthedocs.org`_

.. _VISA: http://www.ivifoundation.org/Downloads/Specifications.htm
.. _`https://github.com/pyvisa/pyvisa-sim/zipball/master`: https://github.com/pyvisa/pyvisa-sim/zipball/master
.. _`https://pyvisa-sim.readthedocs.org`: https://pyvisa-sim.readthedocs.org

.. |Build Status| image:: https://travis-ci.org/pyvisa/pyvisa-sim.svg?branch=master
   :target: https://travis-ci.org/pyvisa/pyvisa-sim