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

from serial import Serial
import json

from database import Sample, Sensor
from sramplatform.packet import Command, Packet, format_uid
from sramplatform.reader import Reader
from sramplatform.logbook import Status

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
        return f"<Device {self.pic:03d}:{format_uid(self.uid)} 0x{self.sram_size:08X}>"

    def __repr__(self):
        return str(self)


class STM32Reader(Reader):
    """Reader implementation for STM32 boards.

    The functionaly of the reader is implemented in the methods called `handle_{command}`.

    Attributes:
        name: Descriptive name of the Reader.
        devices: List of managed devices.
        port: State of the devices and the serial port.

    """

    def __init__(self, board_type: str, port: str, baudrate: int):
        super(STM32Reader, self).__init__(board_type)
        self.devices: Set[Device] = set()
        self.name = board_type

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

    def receive(
        self, timeout: float = 0.1, packet_size=Packet.SIZE, tries=3
    ) -> List[Packet]:
        """Received data from the serial port.

        Args:
            timeout: Time to wait until start receiving information.

        Returns:
            List of packets received.
        """
        ser = self.port["serial"]
        packets = []
        msg = b""

        time.sleep(timeout)

        for _ in range(tries):
            while ser.in_waiting:
                while len(msg) < packet_size:
                    msg += ser.read()
                packets.append(Packet.from_bytes(msg))
                msg = b""
                time.sleep(0.1)

            if not ser.in_waiting and packets:
                return packets

        return packets

    def handle_status(self, props: Dict[str, Any], logger, db_session) -> Status:
        """Show the status of the reader.

        Args:
            props: Dict[str, Any] from the dispatcher

        Returns:
            status of the operation
        """
        logger.results(
            json.dumps(
                {
                    "state": self.port["state"],
                    "devices": [d.__dict__ for d in self.devices],
                }
            )
        )
        return Status.OK

    def handle_power_off(self, props: Dict[str, Any], logger, db_session) -> Status:
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
                return Status.OK
            else:
                logger.warning("Could not power off port")
                return Status.ERR
        except Exception as excep:
            logger.warning(f"Problem powering off port {self.port['path']}: {excep}")
            return Status.ERR

    def handle_power_on(self, props: Dict[str, Any], logger, db_session) -> Status:
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
                return Status.OK
            else:
                logger.warning("Could not power on port")
                return Status.ERR
        except Exception as excep:
            logger.warning(f"Problem powering on port {self.port['path']}: {excep}")
            return Status.ERR

    def handle_ping(self, props: Dict[str, Any], logger, db_session) -> Status:
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        prev_devices = self.devices

        packet = Packet()
        packet.with_command(Command.PING)
        packet.craft()
        self.send(packet.to_bytes())
        packets = self.receive()

        if prev_devices and not packets:
            logger.warning(
                "There were devices connected but now no devices could be identified"
            )
            return Status.ERR

        if not packets:
            logger.warning("No devices could be identified")
            return Status.ERR

        self.devices = set()
        for packet in packets:
            self.devices.add(Device(format_uid(packet.uid), packet.pic, packet.options))

        logger.info("Devices identified correctly")
        logger.results(json.dumps([d.__dict__ for d in self.devices]))
        return Status.OK

    def handle_sensors(self, props: Dict[str, Any], logger, db_session) -> Status:
        """Register the devices connected to the reader.

        Args:
            props: Dictionary containing the message from the dispatcher.

        Returns:
            Dictionary with the status of the operation and metadata if needed.
        """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        for dev in self.devices:
            packet = Packet()
            packet.with_command(Command.SENSORS)
            packet.with_uid(dev.uid)
            packet.craft()
            self.send(packet.to_bytes())
            res = next(iter(self.receive()), None)
            if res is None:
                logger.error(f"Problem reading sensors for device {dev.uid}")
                continue

            sensors_data = res.extract_sensors()
            db_session.insert(
                Sensor(
                    uid=res.uid,
                    board_id=self.name,
                    temperature=sensors_data["temperature"],
                    voltage=sensors_data["voltage"],
                )
            )
            db_session.commit()

        logger.info("Sensors read correctly")
        return Status.OK

    def handle_read(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        # Only store the day the read is done
        current_day = datetime.now()
        current_day = current_day.replace(hour=12, minute=0, second=0)

        for dev in self.devices:
            for offset in range(dev.sram_size // Packet.DATA_SIZE):
                address = Packet.off_to_add(offset)
                packet = Packet()
                packet.with_command(Command.READ)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.craft()
                self.send(packet.to_bytes())
                res = next(iter(self.receive()), None)
                if res is None:
                    logger.warning(f"Problem reading memory of device {dev.uid}")

                db_session.insert(
                    Sample(
                        uid=res.uid,
                        board_id=self.name,
                        pic=dev.pic,
                        address=address,
                        data=",".join([str(d) for d in res.data]),
                        created_at=current_day,
                    )
                )
            db_session.commit()
        logger.info("Memory read correctly")
        return Status.OK

    def handle_write(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        offset = props["offset"]
        dev_id = props["device"]
        device = next(filter(lambda d: d.uid == dev_id, self.devices), None)

        if not device:
            logger.warning(f"Device {dev_id} is not managed")
            return Status.ERR

        max_offset = device.sram_size // Packet.DATA_SIZE

        if offset < 0 or offset > max_offset:
            logger.warning(
                f"Offset {offset} for device {dev_id} must be in range [0, {max_offset}]"
            )
            return Status.ERR

        packet = Packet()
        packet.with_command(Command.WRITE)
        packet.with_uid(device.uid)
        packet.with_options(offset)
        packet.with_data([int(b) for b in props["data"]])
        packet.craft()

        self.send(packet.to_bytes())
        logger.info("Data written correctly")
        return Status.OK

    def handle_write_invert(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        device_list = list(self.devices)
        for dev in device_list[0 : len(self.devices) // 2]:
            num_addresses = dev.sram_size // Packet.DATA_SIZE
            samples = (
                db_session.query(Sample)
                .filter(Sample.uid == dev.uid)
                .order_by(Sample.created_at.asc())
                .limit(num_addresses)
            )

            if not samples:
                logger.warning(
                    f"At least one memory sample has to be read from device {dev.uid}"
                )
                return Status.ERR

            end_offset = (dev.sram_size // Packet.DATA_SIZE) - READ_ONLY_REGIONS
            for offset in range(READ_ONLY_REGIONS, end_offset):
                sample = samples[offset]

                packet = Packet()
                packet.with_command(Command.WRITE)
                packet.with_uid(dev.uid)
                packet.with_options(offset)
                packet.with_data([0xFF ^ int(d) for d in sample.data.split(",")])
                packet.craft()

                self.send(packet.to_bytes())
                time.sleep(0.2)

        logger.info("Data inverted correctly")
        return Status.OK

    def handle_load(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        dev_uid = props["device"]
        device = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not device:
            logger.warning(f"Device {dev_uid} is not managed")
            return Status.ERR

        source = props["source"]
        len_code = len(source)
        data_buf = [ord(c) for c in source] + [ord("\x00")] * (
            Packet.DATA_SIZE - len_code
        )

        packet = Packet()
        packet.with_command(Command.LOAD)
        packet.with_uid(dev_uid)
        packet.with_data(data_buf)
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)
        if res is None:
            logger.warning(f"Problem loading code for device {dev_uid}")
            return Status.ERR

        logger.info(f"Code loaded on device {dev_uid} correctly")
        return Status.OK

    def handle_exec(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        dev_uid = props["device"]
        device = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not device:
            logger.warning(f"Device {dev_uid} is not managed")
            return Status.ERR

        packet = Packet()
        packet.with_command(Command.EXEC)
        packet.with_uid(dev_uid)
        packet.with_options(int(props.get("reset", 0)))
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)

        if res.options == 0:
            logger.info(f"Code executed on device {dev_uid} correctly")
            return Status.OK

        logger.warning(
            f"Code on device {dev_uid} executed with error code {res.options}"
        )
        return Status.ERR

    def handle_retr(self, props: Dict[str, Any], logger, db_session) -> Status:
        """ """
        if not self.devices:
            logger.warning("No devices managed")
            return Status.ERR

        dev_uid = props["device"]
        device = next(filter(lambda d: d.uid == dev_uid, self.devices), None)

        if not device:
            logger.warning(f"Device {dev_uid} is not managed")
            return Status.ERR

        packet = Packet()
        packet.with_command(Command.RETR)
        packet.with_uid(dev_uid)
        packet.craft()
        self.send(packet.to_bytes())
        res = next(iter(self.receive()), None)
        if res is None:
            logger.warning(f"Problem retrieving results from device {dev_uid}")
            return Status.ERR

        numbers = struct.unpack(f"<{Packet.DATA_SIZE // 4}i", bytes(res.data))
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
        return Status.OK
