PyVISA-sim Changelog
====================

0.6.0 (2023-11-27)
------------------

- Fixed debug logging a single character at a time. PR #79
- Fixed issue with `common.iter_bytes` where the masked bits would be incorrect.
  PR #81

0.5.1 (2022-09-08)
------------------

- fix rendering issues in the README

0.5 (2022-09-08)
----------------

- add support for secondary GPIB addresses
- remove last uses of the six package and of ``__future__`` imports

0.4 (2020-10-26)
----------------

- Use SCM based version number PR #53
- Work with PyVISA >= 1.11 PR #53
- Drop support for Python 2, 3.4 and 3.5 PR #53
- Drop support for Python 3.2 (EOL 2016-02-27)
- Drop support for Python 3.3 (EOL 2017-09-29)
- Add support for Python 3.7 and 3.8
- Add tox for project setup and test automation
- Switch from unittest to pytest

.. _03-2015-08-25:

0.3 (2015-08-25)
----------------

-  Fixed bug in get_device_dict. (Issue #37)
-  Move resource name parsing to pyvisa.rname.
-  Implemented query in list_resources.
-  Add support for USB RAW.
-  Warn the user when no eom is specified for device type and use LF.

.. _02-2015-05-19:

0.2 (2015-05-19)
----------------

-  Add support for channels. (Issue #9, thanks MatthieuDartiailh)
-  Add support for error queue. (Issue #26, thanks MatthieuDartiailh)
-  Add support for TCPIP SOCKET. (Issue #29, thanks MatthieuDartiailh)
-  Removed resource string parsing in favour of to pyvisa.rname.
-  Changed find_resource and find_next in favour of list_resources.
-  Implemented new loader with bases and versioning enforcing. (Issue
   #16)
-  Renamed is_resource to bundled in yaml files.
-  Added support for an empty response. (Issue #15, thanks famish99)
-  Several small fixes and better VISA compliance.
-  Better error reporting and debug info.

.. _01-2015-02-12:

0.1 (2015-02-12)
----------------

-  First public release.
-  Basic ASRL INSTR functionality.
-  Basic USB INSTR functionality.
-  Basic TCPIP INSTR functionality.
