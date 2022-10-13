Executing commands
==================

A command refers to an operation that the station can carry out. All of the information necesary to carry such operation should be written to the header of the packet. 

| Command | Command code | Description                                    |
|---------|--------------|------------------------------------------------|
| `ACK`   | 1            | Packet acknowledge                             |
| `PING`  | 2            | Discover devices in a chain                    |
| `READ`  | 3            | Read a region of memory from a device          |
| `WRITE` | 4            | Write values to a region of memory of a device |
| `EXEC`  | 5            | Execut custom loaded code from memory          |
| `ERR`   | 255          | Error during transmision                       |


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

The responses from the station are logged into rabbitmq as a JSON with the fields `status`, `msg`

### Status

This command checks the current status of the station at any given time. It returns the 

```python
{'status': 'OK', 'msg': {'state': 'ON', 'devices': []}}
```

### Ping command

```python
{'status': 'OK', 'msg': {'state': 'ON', 'devices': []}}
```

### Read command

```python
{'status': 'OK', 'msg': {'state': 'ON', 'devices': []}}
```

### Write command

```python
{'status': 'OK', 'msg': {'state': 'ON', 'devices': []}}
```

### Write invert command
 
```python
{'status': 'OK', 'msg': {'state': 'ON', 'devices': []}}
```



