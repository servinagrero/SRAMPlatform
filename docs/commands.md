Executing commands
==================

A command refers to an operation that the station can carry out. All of the information necesary to carry such operation should be written to the header of the packet. 

| Command   | Command code | Description                                     |
|-----------|:------------:|-------------------------------------------------|
| `ACK`     | 1            | Packet acknowledge.                             |
| `PING`    | 2            | Discover devices in a chain.                    |
| `READ`    | 3            | Read a region of memory from a device.          |
| `WRITE`   | 4            | Write values to a region of memory of a device. |
| `SENSORS` | 5            | Read sensors from a device.                     |
| `LOAD`    | 6            | Load code into memory to be interpreted later.  |
| `EXEC`    | 7            | Interpret code stored in memory.                |
| `RETR`    | 8            | Retrieve the results from the code.             |
| `ERR`     | 255          | Error during transmision.                       |


!!! info

    The script `send_command.py` can be used to send one of the predefined commands above to a running agent from the CLI.


Once an agent has been deployed, and a reader has been assigned to it, new messages can be sent to the agent directly as seen below.


```{.py3 title="Sending a message with an agent"}
from fenneq import Agent

# URL and exchange_name have to be the same as the other agents
url = "amqp://user:pass@localhost"
exchange_name = "sram_commands"
topic = "sram.discovery"
agent = Agent(
    url, exchange_name, topic, Agent.JSON
)
msg = {'method': 'READ'}

# Message will be sent to sram.discovery
agent.send(msg)

# The message can be sent to another topic with the same agent
agent.send(msg, name="sram.nucleo") 
```

## Station commands

### Power on
 
Power on the serial port connected to the dispatcher. 

`Parameters`

: 

```python
{"command": "power_on"}
```

`Logging`

: 
| Level   | Description                                  |
|---------|----------------------------------------------|
| INFO    | `Port powered on.`                           |
| WARNING | `Could not power on port.`                   |
| ERROR   | `Problem powering on port {port}: {reason}.` |


### Power off

Power off the serial port connected to the dispatcher.

`Parameters` 

: 

```python
{"command": "power_off"}
```

`Logging`

: 
| Level   | Description                                   |
|---------|-----------------------------------------------|
| INFO    | `Port powered off.`                           |
| WARNING | `Could not power off port.`                   |
| ERROR   | `Problem powering off port {port}: {reason}.` |


### Status

Check whether the serial port of the dispatcher is on or off and the number of devices it is managing.

`Parameters`

: 
```python
{"command": "status"}
```

`Results`

: 

  ```{.py3}
  {
      "state": "ON" | "OFF", 
      "devices": [{"uid": str, "pic": int, "sram_size": int}, ...]
  }
  ```

### Ping

Register devices that are in the chain connected to the serial port.

`Parameters`

: 
```python
{"command": "ping"}
```

`Logging`

: 
| Level   | Description                                                            |
|---------|------------------------------------------------------------------------|
| ERROR   | `Serial port is off. Please turn on the serial port first.`            |
| ERROR   | `There were devices connected but now no devices could be identified.` |
| ERROR   | `No devices could be identified.`                                      |
| WARNING | `Packet {packet} is corrupted.`                                        |

`Results`

: `#!python [{"uid": str, "pic": int, "sram_size": int}, ...]`


### Read

Read all regions of memory from all devices managed by the dispatcher. This command can be done per device and per region of memory but it is performed on all devices and regions in one go.

The ping command has to be executed first.

`Parameters`

: `#!python {"command": "read"}`

`Logging`

: 
| Code    | Description                                                    |
|---------|----------------------------------------------------------------|
| ERROR   | `Serial port is off. Please turn on the serial port first.`    |
| ERROR   | `No devices managed.`                                          |
| ERROR   | `Problem reading memory of device {device} at offset {offset}` |
| WARNING | `Packet {packet} for device {device} is corrupted.`            |
| INFO    | `Finished reading memory of device {device}.`                  |


### Write

Write values to a region of memory of a device managed by the dispatcher.

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "write", "device": str, "data": list[int], "offset": int}
```

`Logging`

: 
| Code  | Description                                                              |
|-------|--------------------------------------------------------------------------|
| ERROR | `Serial port is off. Please turn on the serial port first.`              |
| ERROR | `No devices managed.`                                                    |
| ERROR | `Device {device} is not managed.`                                        |
| ERROR | `Offset {offset} for device {device} must be in range [0, {max_offset}]` |
| ERROR | `Problem writing to device {device} at offset {offset}`                   |
| ERROR | `Packet {packet} for device {device} is corrupted.`                      |
| INFO  | `Data written correctly.`                                                |

### Write invert
 
Write inverted values to half of the devices managed by a dispatcher. Inverted values are calculated based on the first sample (a.k.a. reference sample) of a device. 

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "write_invert"}
```

`Logging`

: 
| Code    | Description                                                             |
|---------|-------------------------------------------------------------------------|
| ERROR   | `Serial port is off. Please turn on the serial port first.`             |
| ERROR   | `No devices managed.`                                                   |
| WARNING | `At least one full memory sample has to be read from device {device}.`  |
| WARNING | `The memory sample for device {device} is not complete.`                |
| ERROR   | `Problem writing inverted values to device {device} at offset {offset}` |
| ERROR   | `Packet {packet} for device {device} is corrupted.`                     |
| DEBUG   | `Wrote inverted values of device {device} at offset {offset}.`          |
| INFO    | `Finished inverting memory of device {device}.`                         |


### Sensors
 
Read the sensors of the devices managed by a dispatcher.

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "sensors"}
```

`Logging`

: 
| Code    | Description                                                 |
|---------|-------------------------------------------------------------|
| ERROR   | `Serial port is off. Please turn on the serial port first.` |
| ERROR   | `No devices managed.`                                       |
| ERROR   | `Problem reading sensors of device {device}.`               |
| WARNING | `Packet {packet} for device {device} is corrupted.`         |

`Results`

: 
```python
{"device": {"uid": str, "pic": int}, "temperature": float, "voltage": float}
```



### Load
 
Load code onto a device managed by the dispatcher. 

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "load", "device": str, "source": str, "offset": int}
```

`Logging`

: 
| Code  | Description                                                 |
|-------|-------------------------------------------------------------|
| ERROR | `Serial port is off. Please turn on the serial port first.` |
| ERROR | `No devices managed.`                                       |
| ERROR | `Device {device} is not managed.`                           |
| ERROR | `Problem loading code for device {device}.`                 |
| ERROR | `Packet {packet} for device {device} is corrupted.`         |
| INFO  | `Code loaded on device {device} correctly.`                 |


### Execute

Execute code loaded into a device managed by the dispatcher and write the results to memory.

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "exec", "device": str, "reset": bool}
```

`Logging`

: 
| Code  | Description                                                 |
|-------|-------------------------------------------------------------|
| ERROR | `Serial port is off. Please turn on the serial port first.` |
| ERROR | `No devices managed.`                                       |
| ERROR | `Device {device} is not managed.`                           |
| ERROR | `Problem executing code on device {device}.`                |
| ERROR | `Packet {packet} for device {device} is corrupted.`         |
| ERROR | `Code on device {device} executed with error code {code}.`  |
| INFO  | `Code executed on device {device} correctly.`               |

### Retrieve
 
Retrieve the results from executing loaded code from a device managed by the dispatcher.

The ping command has to be executed first.

`Parameters`

: 
```python
{"command": "retr", "device": str}
```

`Logging`

: 
| Code  | Description                                                 |
|-------|-------------------------------------------------------------|
| ERROR | `Serial port is off. Please turn on the serial port first.` |
| ERROR | `No devices managed.`                                       |
| ERROR | `Device {device} is not managed.`                           |
| ERROR | `Problem retrieving results from device {device}.`          |
| ERROR | `Packet {packet} for device {device} is corrupted.`         |
| INFO  | `Results retrieved correctly from device {device}.`         |

`Results`

: 
```python
{"raw_bytes": bytes, "int": list[int], "string": str}
```
