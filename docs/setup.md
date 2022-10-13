Open-platform for the acquisition of SRAM-based PUFs from Micro-Controllers

# Setup guide

This section will describe the requirements needed to deploy a station. Here we describe first the software requirements followed by the hardware requirements and lastly, their physical installation and deployment.

## Python dependencies

Python dependencies can be installed by using the requirements.txt file provided. It is recomended, but not mandatory, to create a virtual environment to install the requirements. The following code describes the process of creating a virtual env and installing the dependencies.


```{.sh title="Using pip"}
$ python3 -m venv /path/to/virtual_env
$ source /path/to/virtual_env/bin/activate
$ pip install -r requirements.txt
$ deactivate # To exit the virtual environment
```

```{.sh title="Using poetry"}
$ cd /path/to/SRAMPlatform
$ poetry install
```

## Device source code

This project contains code for two different STM32 boards. Each project is managed by STM32Cube. Devices should be programmed using the same software.

## Other dependencies

The platform relies on `RabbitMQ <https://www.rabbitmq.com/>`_ for the communication and queing of commands, and `PostgreSQL <https://www.postgresql.org/>`_ for the storage. They can be deployed easily thanks to `Docker <https://www.docker.com/>`_.

!!! info
    The access to the database is carried out with an ORM, so the user should be able to swap PostreSQL for another database in case they need.

The file **docker-compose.yml** provides the template necesary to launch those services. However, it is necesary to update the configuration values in the file before deploying. The main parameters to modify are user and password of both RabbitMQ and PostgreSQL. The other important parameter is the volume configuration for postgreSQL, (e.g. where to store the data in the computer). The path before the semicolon points to the path in the computer where to store the samples. **The path after the semicolorn should not be modified**.

!!! note
    We can think of docker as a virtual machine. We can provide some paths (here `volumes`) in the computer that will get linked to a path inside the container. The syntax is ``path_in_computer:path_in_docker``.

```{.yaml title="Example of docker-compose file" hl_lines=27}
--8<-- "./docker-compose.yml"
```

```{.sh title="Start services with docker-compose"}
$ docker-compose up -d -f /path/to/docker-compose.yml
$ docker-compose up -d # If in the same path as docker-compose.yml
```

```{.sh title="Stop docker services"}
$ docker-compose down # In the same path as docker-compose.yml
```

Deployment services
-------------------

Once all the software is installed and the hardware is properly connected, the station should be ready for deployment.
The deployment of the station can be carried out with the use of systemd services.

```python
#!/usr/bin/env python3

from sramplatform import Dispatcher, ConnParameters

# Custom implementation of Reader
from customreader import CustomReader

reader = CustomReader("Discovery", 0, 125_000)

params = ConnParameters("rabbitmq_user", "rabbitmq_pass")
platform = Dispatcher(
    params, "exchange_commands", "station_name", "exchange_logs"
)

platform.add_command({"method": "read"}, reader.handle_read)
platform.add_command({"method": "write", "data": True}, reader.handle_write)

if __name__ == '__main__':
  platform.run()
```

```txt
[Unit]
Description=SRAM Reliability Platform
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
WorkingDirectory=/path/to/SRAMPlatform
ExecStart=/path/to/virtualenv/bin/python3 main.py

[Install]
WantedBy=multi-user.target
```

Operations can be scheduled by using the send_command.py script provided and a systemd timer (very similar to a cron job). The following example illustrates how to create the files necesary to power off the platform every friday at 17:00.


```text
[Unit]
Description=Power off the SRAM Platform

[Timer]
OnCalendar=Fri *-*-* 17:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```text
[Unit]
Description=Power off the SRAM Platform
After=network.target

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/path/to/SRAMPlatform
ExecStart=/path/to/virtualenv/bin/python3 send_command.py "OFF"

[Install]
WantedBy=multi-user.target
```
