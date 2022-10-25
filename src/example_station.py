#!/usr/bin/env python3

from sramplatform import Dispatcher, from_config
from stm32reader import STM32Reader
from database import dbmanager

CONFIG_PATH = "/path/to/config.yml"
agent, reader, logger = from_config(CONFIG_PATH, STM32Reader)
platform = Dispatcher(agent, logger, dbmanager)

platform.add_command({"command": "status"}, reader.handle_status)
platform.add_command({"command": "ping"}, reader.handle_ping)
platform.add_command({"command": "sensors"}, reader.handle_sensors)
platform.add_command({"command": "power_off"}, reader.handle_power_off)
platform.add_command({"command": "power_on"}, reader.handle_power_on)
platform.add_command({"command": "read"}, reader.handle_read)
platform.add_command(
    {"command": "write", "data": True, "offset": int}, reader.handle_write
)
platform.add_command({"command": "write_invert"}, reader.handle_write_invert)

platform.add_command(
    {"command": "load", "device": str, "source": str}, reader.handle_load
)
platform.add_command(
    {"command": "exec", "device": str, "reset": bool}, reader.handle_exec
)
platform.add_command({"command": "retr", "device": str}, reader.handle_retr)

if __name__ == "__main__":
    platform.run()
