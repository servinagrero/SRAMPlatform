# Communication protocol

As it has been previously stated the **reader** is in charge of creating the necesary packets that will be sent to the devices to carry out the commands.

The commands are sent to the station by means of a RabbitMQ channel, and the reader is dispatched through a [fenneq agent](https://github.com/servinagrero/fenneq.git) listening for the proper messages. The documentation of fenneq provides in detail explanations on how to 


As an example, a generic reader can be implemented in python with the following interface:

```{.py3 title="Definition of the Reader Interface"}
class Reader:
    def __init__(self, name):
        self.devices = []
        self.name = name

    def send(self, data: bytes):
        raise NotImplementedError

    def receive(self):
        raise NotImplementedError()
```

!!! info
    This station already includes the definition of a reader for STM32 devices by means of USART.


```{.py3 title="Example of combining an agent and a reader"}
from fenneq import Agent

from reader import STM32Reader
from database import LogLevel

# Reader called DISCOVERY, listening on USB port 1 @ 125_000
reader = STM32Reader("DISCOVERY", 1, baudrate=125_000)

# Url to connect to the RabbitMQ interchange
url = "amqp://user:pass@localhost"
exchange_name = "sram_commands"
# Commands sent to sram.discovery will be read by this agent.
# For more detail on how to setup topics follow the official documentation
# rabbitmq topic documentation
topic = "sram.discovery"
agent = Agent(
    url, exchange_name, topic, Agent.JSON
)

# The function handle_read will be called when a message from sram_commands
# sent to sram.discovery contains the values {'method': "READ"}
@agent.on({"method": "READ"})
def handle_read(ch, method_frame, props, body):
    res = reader.handle_read(body)


# Multiple functions can be assigned to the same message.
@agent.on({"method": "READ"})
def handle_read_second(ch, method_frame, props, body):
    res = reader.handle_read_second(body)


# Moreover, multiple agents can use the same callback.
@agent.on({"method": "READ"})
@agent_two.on({"command": "read"})
def handle_read(ch, method_frame, props, body):
    res = reader.handle_read_second(body)
```

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

### Working with packets

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






