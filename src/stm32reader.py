#!/usr/bin/env python3

import logging
import sys
import time
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from subprocess import run
from typing import Dict, List, Optional, Set, Union, Any
from collections import deque

from serial import Serial
import json

from database import Sample, Sensor
from sramplatform.packet import Command, Packet, format_uid, offset_to_address
from sramplatform.reader import Reader
from sramplatform.logbook import CommandError

# Number of regions of memory that are read only
READ_ONLY_REGIONS = 5


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

    def __str__(self):
        return f"{self.pic:03d}:{format_uid(self.uid)}"

    def __repr__(self):
        return f"<Device {self.pic:03d}:{format_uid(self.uid)} 0x{self.sram_size:08X}>"


class STM32Reader(Reader):
    """Reader implementation for STM32 boards.

    The functionaly of the reader is implemented in the methods called `handle_{command}`.

    Attributes:
        name: Descriptive name of the Reader.
        devices: List of managed devices.
        port: State of the devices and the serial port.
    """

    def __init__(self, board_type: str, port: str, baudrate: int, data_size: int):
        super(STM32Reader, self).__init__(board_type)
        self.devices: List[Device] = []
        self.name = board_type
        self.data_size = data_size

        port_path = Path(port)
        if not port_path.exists():
            print(f"Port {port_path} does not exist")
            sys.exit(1)

        ser = Serial(port_path.as_posix(), baudrate, timeout=None)
        self.port = {"state": "ON", "serial": ser, "path": port_path}

    def send(self, data: bytes):
        """Transmit data through the serial port.

        Args:
            data: Bytes to sent.
        """
        ser = self.port["serial"]
        ser.flushInput()
        ser.write(data)
        ser.flushOutput()

    def receive(self, timeout: float = 0.2, tries=50) -> List[Packet]:
        """Received data from the serial port.

        Args:
            timeout: Time to wait until start receiving information.

        Returns:
            List of packets received.
        """
        packet_size = Packet.full_size(self.data_size)

        ser = self.port["serial"]
        ser.flushInput()
        packets = []
        msg = b""

        time.sleep(timeout)
        checks = deque(maxlen=tries // 2)
        for _ in range(tries):
            checks.appendleft(ser.in_waiting)
            while ser.in_waiting:
                while len(msg) < packet_size:
                    msg += ser.read()
                packets.append(Packet.from_bytes(self.data_size, msg))
                msg = b""

            if all(num == 0 for num in checks) and packets:
                return packets
            time.sleep(0.05)

        return packets

    def handle_status(self, props: Dict[str, Any], logger, db_session):
        """Show the status of the reader.

        Args:
            props: Dict[str, Any] from the dispatcher
            logger: Logger instance to log data.
            db_session: DBManager instance to query and insert data.

        Returns:
            Status of the operation
        """
        logger.results(
            json.dumps(
                {
                    "state": self.port["state"],
                    "devices": [d.__dict__ for d in self.devices],
                }
            )
        )

    def handle_power_off(self, props: Dict[str, Any], logger, db_session):
        """Power off the serial port.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        try:
            p = run(["ykushcmd", "-d", "a"])
            if p.returncode == 0:
                self.port["state"] = "OFF"
                logger.info("Port powered off")
            else:
                logger.warning("Could not power off port")
                raise CommandError
        except Exception as excep:
            raise CommandError(
                f"Problem powering off port {self.port['path']}: {excep}"
            ) from excep

    def handle_power_on(self, props: Dict[str, Any], logger, db_session):
        """Power on the serial port.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        try:
            p = run(["ykushcmd", "-u", "a"])
            if p.returncode == 0:
                self.port["state"] = "ON"
                logger.info("Port powered on")
            else:
                logger.warning("Could not power on port")
                raise CommandError
        except Exception as excep:
            raise CommandError(
                f"Problem powering on port {self.port['path']}: {excep}"
            ) from excep

    def handle_ping(self, props: Dict[str, Any], logger, db_session):
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        status_correct: Optional[bool] = None
        prev_devices = self.devices

        packet = Packet(self.data_size)
        packet.with_command(Command.PING)
        packet.craft()
        self.send(packet.to_bytes())
        packets = self.receive()

        if self.port["state"] == "OFF":
            raise CommandError(
                "Serial port is off. Please turn on the serial port first"
            )

        if prev_devices and not packets:
            raise CommandError(
                "There were devices connected but now no devices could be identified"
            )

        if not packets:
            raise CommandError("No devices could be identified")

        devices: List[Device] = []
        for packet in packets:
            if not packet.check_crc():
                logger.warning(f"Packet {packet!s} is corrupted")
                status_correct = False
            else:
                devices.append(
                    Device(format_uid(packet.uid), packet.pic, packet.options)
                )

        self.devices = devices
        if status_correct is None:
            logger.results(json.dumps([d.__dict__ for d in self.devices]))

    def handle_sensors(self, props: Dict[str, Any], logger, db_session):
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        for dev in self.devices:
            packet = Packet(self.data_size)
            packet.with_command(Command.SENSORS)
            packet.with_uid(dev.uid)
            packet.craft()
            self.send(packet.to_bytes())
            res = next(iter(self.receive()), None)
            if res is None:
                logger.error(f"Problem reading sensors for device {dev}")
                continue

            if not packet.check_crc() or packet.command == Command.ERR:
                logger.warning(f"Packet {packet!s} for device {dev} is corrupted")
                continue

            sensors_data = res.extract_sensors()

            logger.results(
                json.dumps(
                    {
                        "device": {"uid": dev.uid, "pic": dev.pic},
                        "temperature": sensors_data["temperature"],
                        "voltage": sensors_data["voltage"],
                    }
                )
            )

            db_session.add(
                Sensor(
                    uid=format_uid(res.uid),
                    board_type=self.name,
                    temperature=sensors_data["temperature"],
                    voltage=sensors_data["voltage"],
                )
            )
            db_session.commit()

    def handle_read(self, props: Dict[str, Any], logger, db_session):
        """ """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        # Only store the day the read is done
        current_day = datetime.now()
        current_day = current_day.replace(hour=12, minute=0, second=0)

        for dev in self.devices:
            for offset in range(dev.sram_size // self.data_size):
                address = offset_to_address(self.data_size, offset)
                packet = Packet(self.data_size)
                packet.with_command(Command.READ)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.craft()
                self.send(packet.to_bytes())
                res = next(iter(self.receive()), None)
                if res is None:
                    logger.error(
                        f"Problem reading memory of device {dev} at offset {offset}"
                    )
                    continue

                if not packet.check_crc() or packet.command == Command.ERR:
                    logger.warning(f"Packet {packet!s} is corrupted")
                    continue

                db_session.add(
                    Sample(
                        board_type=self.name,
                        uid=format_uid(res.uid),
                        pic=dev.pic,
                        address=address,
                        data=",".join([str(d) for d in res.data]),
                        created_at=current_day,
                    )
                )
            db_session.commit()

            logger.info(f"Finished reading memory of {dev}")

    def handle_write(self, props: Dict[str, Any], logger, db_session):
        """ """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        offset = props["offset"]
        dev_id = props["device"]
        dev = next(filter(lambda d: d.uid == dev_id, self.devices), None)

        if not dev:
            raise CommandError(f"Device {dev.id} is not managed")

        max_offset = dev.sram_size // self.data_size

        if offset < 0 or offset > max_offset:
            raise CommandError(
                f"Offset {offset} for device {dev_id} must be in range [0, {max_offset}]"
            )

        packet = Packet(self.data_size)
        packet.with_command(Command.WRITE)
        packet.with_uid(dev.uid)
        packet.with_options(offset)
        packet.with_data([int(b) for b in props["data"]])
        packet.craft()

        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)
        if res is None:
            raise CommandError(
                f"Problem writing to memory of device {dev.pic}{dev.uid} at offset {offset}"
            )

        if not res.check_crc() or res.command == Command.ERR:
            raise CommandError(f"Packet {packet!s} is corrupted")

        logger.info("Data written correctly")

    def handle_write_invert(self, props: Dict[str, Any], logger, db_session):
        """
        We assume that a reader handles only one type of device,
        So all devices *should* have the same memory regions.

        Get first all different regions and later check that a device
        has at least one sample of all of them.
        """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        device_list = list(self.devices)
        for dev in device_list[: len(self.devices) // 2]:
            num_addresses = dev.sram_size // self.data_size
            samples = (
                db_session.query(Sample)
                .filter(Sample.uid == dev.uid)
                .order_by(Sample.address.asc(), Sample.created_at.asc())
                .limit(num_addresses)
                .all()
            )

            if not samples:
                logger.warning(
                    f"At least one full memory sample has to be read from device {dev}"
                )
                continue

            if len(samples) != num_addresses:
                logger.warning(f"The memory sample for device {dev} is not complete")
                continue

            end_offset = (num_addresses) - READ_ONLY_REGIONS
            for offset in range(READ_ONLY_REGIONS, end_offset):
                sample = samples[offset]
                packet = Packet(self.data_size)
                packet.with_command(Command.WRITE)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.with_data([0xFF ^ int(d) for d in sample.data.split(",")])
                packet.craft()

                self.send(packet.to_bytes())
                res = next(iter(self.receive()), None)
                if res is None:
                    logger.error(
                        f"Problem writing inverted values of device {dev.pic}{dev.uid} at offset {offset}"
                    )
                    continue

                if not res.check_crc() or res.command == Command.ERR:
                    logger.warning(f"Packet {packet!s} is corrupted")
                    continue

            logger.info(f"Finished inverting memory of device {dev}")

    def handle_load(self, props: Dict[str, Any], logger, db_session):
        """ """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        dev_uid = props["device"]
        dev = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not dev:
            raise CommandError(f"Device {dev.uid} is not managed")

        source = props["source"]
        len_code = len(source)
        data_buf = [ord(c) for c in source] + [ord("\x00")] * (
            self.data_size - len_code
        )

        packet = Packet(self.data_size)
        packet.with_command(Command.LOAD)
        packet.with_uid(dev_uid)
        packet.with_data(data_buf)
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)
        if res is None:
            raise CommandError(f"Problem loading code for device {dev}")

        if not res.check_crc() or res.command == Command.ERR:
            raise CommandError(f"Packet {packet!s} is corrupted")

        logger.info(f"Code loaded on device {dev} correctly")

    def handle_exec(self, props: Dict[str, Any], logger, db_session):
        """ """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        dev_uid = props["device"]
        dev = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not dev:
            raise CommandError(f"Device {dev_uid} is not managed")

        packet = Packet(self.data_size)
        packet.with_command(Command.EXEC)
        packet.with_uid(dev_uid)
        packet.with_options(int(props.get("reset", 0)))
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)

        if res is None:
            raise CommandError(f"Problem executing code on device {dev.pic}{dev.uid}")

        if not res.check_crc() or res.command == Command.ERR:
            raise CommandError(f"Packet {packet!s} is corrupted")

        if res.options != 0:
            raise CommandError(
                f"Code on device {dev} executed with error code {res.options}"
            )
        logger.info(f"Code on device {dev} executed correctly")

    def handle_retr(self, props: Dict[str, Any], logger, db_session):
        """ """
        if self.port["state"] == "OFF":
            raise CommandError("Serial port is off. Turn on the serial port first")

        if not self.devices:
            raise CommandError("No devices managed")

        dev_uid = props["device"]
        dev = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not dev:
            raise CommandError(f"Device {dev_uid} is not managed")

        packet = Packet(self.data_size)
        packet.with_command(Command.RETR)
        packet.with_uid(dev.uid)
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)
        if res is None:
            raise CommandError(f"Problem retrieving results from device {dev}")

        if not res.check_crc() or res.command == Command.ERR:
            raise CommandError(f"Packet {packet!s} is corrupted")

        numbers = struct.unpack(f"<{self.data_size // 4}i", bytes(res.data))
        numbers_str = map(str, numbers)
        numbers_str = map(
            lambda n: n.replace("10", "\n").replace("32", " "), numbers_str
        )
        logger.info(f"Results retrieved correctly from device {dev_uid}")

        logger.results(
            json.dumps(
                {
                    "raw_bytes": res.data,
                    "int": numbers,
                    "string": "".join(numbers_str),
                }
            )
        )
