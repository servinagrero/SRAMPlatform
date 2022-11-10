## Packet based protocol

The communication between a reader and a device chain is performed using a custom packet based protocol.

The source code documentation of the packet can be found :doc:`here <packet>`.

| Field    | Encoding           | Description                                           |
|----------|--------------------|-------------------------------------------------------|
| Method   | uint8_t            | Type of packet. See [commands](commands.md)           |
| PIC      | uint16_t           | `Position In Chain`. Index of the device in the chain |
| Options  | uint16_t           | Metadata for the packet                               |
| UID      | char[25]           | Universal ID of the device                            |
| Checksum | uint32_t           | Checksum of the packet                                |
| Data     | uint8_t[DATA_SIZE] | Actual data of the packet                             |


The **DATA_SIZE** can be defined by the user, but it has to be small than the smallest SRAM size of a device in the chain.

## Working with packets

```{.py3 title="Example of creation of a packet" hl_lines=11}
packet = Packet() # Generate a packet with default values

# The following are the default values
packet.with_method(Method.Ping)
packet.with_options(0x0)
packet.with_checksum(0)
packet.with_pic(1)
packet.with_uid("DEVICE ID")
packet.with_data([0x0, ..., 0x0])

packet.craft() # Craft the packet to send it

# The packet can now be used by calling `to_bytes`
print(packet.to_bytes())
```

!!! warning

    Even if the packet has the default configuration, is is necesary to craft it before sending it, otherwise it will raise a ``ValueError``. The method `is_crafted` returns ``True`` if the packet is ready to be sent.






