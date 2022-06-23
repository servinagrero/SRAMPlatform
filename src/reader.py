#!/usr/bin/env python3

import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from subprocess import run
from typing import Dict, Set, Optional

from serial import Serial

from database import DBManager, Sample, Sensor, LogLevel
from packet import Packet, Method


class Status(Enum):
    #: A command was carried out without errors
    OK = "OK"
    #: There were errors during the execution of a command
    ERR = "ERR"


@dataclass
class Device:
    """Class to represent a device."""

    #: Universal ID of the device
    uid: str

    #: Position In Chain of the device.
    pic: int

    #: Size, in bytes, of the device's SRAM.
    sram_size: int

    def __eq__(self, other):
        return self.uid == other.uid and self.pic == other.pic

    def __hash__(self):
        return hash(("uid", self.uid, "pic", self.pic))


class STM32Reader:
    """Reader implementation for STM32 boards.

    The functionaly of the reader is implemented in the methods called `handle_{method}`.

    Attributes:
        name: Descriptive name of the Reader.
        devices: List of managed devices.
        port: State of the devices and the serial port.

    .. todo::
        * Make the port implementation universal.
    """

    def __init__(self, name: str, port: int, baudrate: int):
        self.devices: Set[Device] = Set()
        self.name = name

        port_path = Path(f"/dev/ttyUSB{port}")
        if not port_path.exists():
            print(f"Port {port_path} does not exist")
            sys.exit(1)

        self.port = {
            "state": "ON",
            "serial": Serial(port_path.as_posix(), baudrate, timeout=None),
        }
        self.db_session = DBManager("postgres://username:password@localhost:5432/database")

    def __transmit_data(self, data: bytes, timeout: float = 0.5, wait_for_rx=True):
        """Transmit data through the serial port and parse the result as packets.

        Args:
            data: Bytes to sent.
            timeout: Time to wait until start receiving information.
            wait_for_rx: If True, wait until packets are received.

        Returns:
            List of packets received.
        """
        packets = []
        msg = b""
        ser = self.port["serial"]

        ser.flushInput()
        ser.write(data)
        ser.flushOutput()

        time.sleep(timeout)

        if wait_for_rx is False:
            return []

        while ser.in_waiting:
            while len(msg) < Packet.SIZE:
                msg += ser.read()
            packets.append(Packet.from_bytes(msg))
            msg = b""
            time.sleep(0.1)

        return packets

    def log(self, node: str, level: LogLevel, message: str):
        """
        Args:
            node: Name of the node
            level: Severity level of the message.
            message: Message to log.
        """
        self.db_session.log(node, level, message)

    def log_operation_status(self, node, res, tag, method=None):
        msg = ""
        if method:
            msg += f"{method} - "
        if res.get("message", None):
            msg += f'{res.get("message")} - '
        self.log(node, res.get("status", "WARNING"), f"{msg}{tag}")

    def handle_status(self, props: Optional[Dict] = None) -> Dict:
        """Show the status of the reader.

        Args:
            props: Message from the dispatcher

        Returns:
            status of the operation
        """
        return {
            "status": Status.OK,
            "data": {
                "state": self.port["state"],
                "devices": [d.__dict__ for d in self.devices],
            },
        }

    def handle_poweroff(self, props: Optional[Dict] = None):
        """Power off the serial port.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        run("ykushcmd -d a", shell=True)
        self.port["state"] = "OFF"
        return {"status": Status.OK}

    def handle_poweron(self, props: Optional[Dict] = None):
        """Power on the serial port.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        run("ykushcmd -u a", shell=True)
        self.port["state"] = "ON"
        return {"status": Status.OK}

    def handle_ping(self, props: Optional[Dict] = None):
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        self.devices = Set()

        packet = Packet()
        packet.with_method(Method.PING)
        packet.craft()
        packets = self.__transmit_data(packet.to_bytes())
        if not packets:
            return {
                "status": Status.ERR,
                "level": LogLevel.Warning,
                "message": "No devices could be identified",
            }

        for p in packets:
            self.devices.add(Device(p.uid, p.pic, p.options))

        return {"status": Status.OK}

    def handle_sensors(self, props: Optional[Dict] = None):
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        if not self.devices:
            return {
                "status": Status.ERR,
                "level": LogLevel.Info,
                "message": "There are no devices managed",
            }

        for dev in self.devices:
            packet = Packet()
            packet.with_method(Method.SENSORS)
            packet.with_uid(dev.uid)
            packet.craft()
            res = self.__transmit_data(packet.to_bytes())[0]
            sensors_data = res.extract_sensors()
            self.db_session.insert(
                Sensor(
                    uid=res.uid,
                    board_id=self.name,
                    temperature=sensors_data["temperature"],
                    voltage=sensors_data["voltage"],
                )
            )
            self.db_session.commit()
        return {"status": Status.OK}

    def handle_read(self, props: Optional[Dict] = None):
        if not self.devices:
            return {
                "status": Status.ERR,
                "level": LogLevel.Info,
                "message": "There are no devices managed",
            }

        # Only store the day the read is done
        current_day = datetime.now()
        current_day = current_day.replace(hour=12, minute=0, second=0)

        for dev in self.devices:
            for offset in range(dev.sram_size // Packet.DATA_SIZE):
                address = Packet.off_to_add(offset)
                packet = Packet()
                packet.with_method(Method.READ)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.craft()
                res = self.__transmit_data(packet.to_bytes())[0]
                self.db_session.insert(
                    Sample(
                        uid=res.uid,
                        board_id=self.name,
                        pic=dev.pic,
                        address=address,
                        data=",".join([str(d) for d in res.data]),
                        created_at=current_day,
                    )
                )
            self.db_session.commit()

        return {"status": Status.OK}

    def handle_write(self, props: Optional[Dict] = None):
        """ """

        device_list = list(self.devices)
        for dev in device_list[0 : len(self.devices) // 2]:
            num_addresses = dev.sram_size // 512
            samples = (
                self.db_session.session.query(Sample)
                .filter(Sample.uid == dev.uid)
                .order_by(Sample.created_at.asc())
                .limit(num_addresses)
            )

            if not samples:
                return {
                    "status": Status.ERR,
                    "message": f"No samples read from the device {dev.uid}",
                }

            # We need to remove some of the address to prevent writing necessary code
            for offset in range(5, (dev.sram_size // 512) - 5):
                sample = samples[offset]

                packet = Packet()
                packet.with_method(Method.WRITE)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.with_data([0xFF ^ int(d) for d in sample.data.split(",")])
                packet.craft()

                self.__transmit_data(packet.to_bytes(), wait_for_rx=False)
                time.sleep(0.2)

        return {"status": Status.OK}
