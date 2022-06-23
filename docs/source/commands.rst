Commands
========

A command refers to an operation that the station can carry out. As of today, the station can carry out `READ`, `WRITE` and `WRITE_INVERT`. This information is stored in the header of the packet.

.. list-table::
    :header-rows: 1

    * - Method
      - Method code
      - Description
    * - ACK
      - 1
      - Packet acknowledge.
    * - PING
      - 2
      - Discover devices in a chain.
    * - READ
      - 2
      - Read a region of memory from a device.
    * - WRITE
      - 2
      - Write values to a region of memory to a device.
    * - EXEC
      - 2
      - Execute custom code loaded from memory. (``WIP``)
    * - ERR
      - 255
      - Error during transmision.


.. note::

    The script ``send_command.py`` can be used to send one of the predefined commands above to a running agent from the CLI.


Read command
~~~~~~~~~~~~

Write command
~~~~~~~~~~~~~

Write invert command
~~~~~~~~~~~~~~~~~~~~
