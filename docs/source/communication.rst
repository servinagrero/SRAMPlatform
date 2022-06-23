Communication
=============

The source code documentation of the packet can be found :doc:`here <packet>`.

.. list-table::
    :header-rows: 1

    * - Field 
      - Size
      - Encoding
      - Description
    * - Method
      - 1
      - Unsigned char
      - Type of packet. Described in detail in :doc:`commands`.
    * - PIC
      - 1
      - Unsigned char
      - Short for `Position In Chain`. Index of the device in the chain.
    * - Options
      - 1
      - Unsigned short
      - Metadata for the packet.
    * - UID
      - 25
      - chars
      - Universal ID.
    * - Checksum
      - 1
      - Unsigned int
      - Checksum for the packet.
    * - Data
      - DATA_SIZE
      - Unsigned char
      - Type of packet.

The protocol of communication is custom made. Is a packet based protocol contaning a header and data.

.. code-block:: python

  packet = Packet() # Generate a packet with default values

  packet.with_method(Method.Ping)
  packet.with_options(0x0)
  packet.with_checksum(0)
  packet.with_pic(1)
  packet.with_uid("DEVICE ID")
  packet.with_data([0x0, ..., 0x0])
  
  packet.craft() # Craft the final packet to sent it

Even if the packet has the default configuration, is is necesary to craft it before sending it, otherwise it will raise a ``ValueError``. The method :meth:`~packet.Packet.is_crafted` returns ``True`` if the packet is ready to be sent.








