:orphan:


PyVISA-sim: Simulator backend for PyVISA
========================================

.. image:: _static/logo-full.jpg
   :alt: PyVISA


PyVISA-sim is a backend for PyVISA_. It allows you to simulate devices
and therefore test your applications without having real instruments connected.

You can select the PyVISA-sim backend using **@sim** when instantiating the
visa Resource Manager:

    >>> import visa
    >>> rm = visa.ResourceManager('@sim')
    >>> rm.list_resources()
    ('ASRL1::INSTR')
    >>> inst = rm.open_resource('ASRL1::INSTR', read_termination='\n')
    >>> print(inst.query("?IDN"))


That's all! Except for **@sim**, the code is exactly what you would write in order to
use the NI-VISA backend for PyVISA.

You can write your own simulators. See :ref:`definitions` to find out how.


Installation
============

Using pip::

    pip install -U pyvisa-sim

You can report a problem or ask for features in the `issue tracker`_.

.. _PyVISA: http://pyvisa.readthedocs.org/
.. _PyPI: https://pypi.python.org/pypi/PyVISA-sim
.. _GitHub: https://github.com/hgrecco/pyvisa-sim
.. _`issue tracker`: https://github.com/hgrecco/pyvisa-sim/issues

