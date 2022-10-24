#!/usr/bin/env python3

import struct
from enum import Enum
from typing import Dict, List, Optional, Union


class Command(Enum):
    """Command the platform should execute."""

    # Packet has been received correctly.
    ACK = 1
    # Identify devices in a chain.
    PING = 2
    # Read a region of memory.
    READ = 3
    # Write to a region of memory.
    WRITE = 4
    # Read the sensors of a device.
    SENSORS = 5
    # Load custom code in a device.
    LOAD = 6
    # Execute custom code on a device.
    EXEC = 7
    # Receive results from executing code.
    RETR = 8
    # Error when receiveng a packet.
    ERR = 255


def format_uid(uid: Union[str, bytes]) -> str:
    """Format a device UID.

    If the uid is bytes, remove the null terminator.

    Args:
        uid: UID of the device.

    Returns:
        Ther formmated UID as a string.
    """
    if isinstance(uid, str):
        return uid
    return uid.decode("ascii").split("\x00")[0]


class Packet:
    """Packet used for the communication protocol.

    Attributes:
        command: Command the platform should execute.
        pic: Position In Chain of the device.
        options: Metadata for the packet.
        uid: UID of the device.
        data: Actual data of the packet.
        bytes: Bytes representation of the packet.
        checksum: CRC of the packet for integrity.
    """

    #: How many bytes of data the packet holds.
    DATA_SIZE = 512

    __bytes_fmt = f"<BBH25sI{DATA_SIZE}B"

    #: Total size of the packet.
    SIZE = struct.calcsize(__bytes_fmt)

    def __init__(self):
        self.__command: int = Command.PING.value
        self.__pic: int = 0
        self.__options: int = 0x0
        self.__uid: str = "0" * 25
        self.__data: List[int] = [0x7] * Packet.DATA_SIZE
        self.__bytes: Optional[bytes] = None
        self.checksum: Optional[int] = None

    def __str__(self):
        checksum = self.checksum or 0
        return (
            f"<Packet {Command(self.__command).name} "
            f"{self.__pic:03d}:{format_uid(self.__uid)} "
            f"[0x{self.__options:04X}] "
            f"CRC(0x{checksum:04X})>"
        )

    def __repr__(self):
        checksum = self.checksum or 0
        return (
            f"<Packet {Command(self.__command).name} "
            f"{self.__pic:03d}:{format_uid(self.__uid)} "
            f"[0x{self.__options:04X}] "
            f"CRC(0x{checksum:04X}) "
            f"{bytes(self.__data)}>"
        )

    @property
    def command(self):
        "Getter for command"
        return self.__command

    @property
    def pic(self):
        "Getter for pic"
        return self.__pic

    @property
    def options(self):
        "Getter for options"
        return self.__options

    @property
    def uid(self):
        "Getter for uid"
        return self.__uid

    @property
    def data(self):
        "Getter for data"
        return self.__data

    @classmethod
    def off_to_add(cls, offset: int, sram_start: int = 0x20000000) -> str:
        """Convert an offset in memory to absolute memory address.

        Args:
            offset: Offset from the start of the SRAM.
            sram_start: Byte representing the start of the SRAM. 0x20000000 by default.

        Raises:
            ValueError: If offset is negative.

        Returns:
            Address formated as 0xXXXXXXXX.
        """
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return f"0x{sram_start + (offset * cls.DATA_SIZE):08X}"

    def with_command(self, command: Union[int, Command]):
        """Set the command of the packet."""
        if isinstance(command, Command):
            self.__command = command.value
        else:
            self.__command = command

    def with_pic(self, pic: int):
        """Set the pic of the packet."""
        self.__pic = pic

    def with_uid(self, uid: str):
        """Set the uid of the packet."""
        self.__uid = uid

    def with_options(self, options: int):
        """Set the options of the packet."""
        self.__options = options

    def with_data(self, data: list[int]):
        """Set the data of the packet."""
        self.__data = data

    def with_checksum(self, checksum: int):
        """Set the checksum of the packet."""
        self.checksum = checksum

    def is_crafted(self) -> bool:
        """Check if a packet is ready to be sent.

        Returns:
            True if bytes is not None.
        """
        return self.__bytes is not None

    def craft(self):
        """Craft a packet to send.

        Calculate the checksum if it hasn't been calculated yet,
        and create the bytes representation of the packet.
        """
        if isinstance(self.__uid, bytes):
            uid = self.__uid
        else:
            uid = bytes(self.__uid, "utf-8")

        if self.checksum is None:
            self.__bytes = struct.pack(
                self.__bytes_fmt,
                self.__command,
                self.__pic,
                0,
                uid,
                self.__options,
                *self.__data,
            )
            self.checksum = sum(bytearray(self.__bytes)) % 0xFFFF
        self.__bytes = struct.pack(
            self.__bytes_fmt,
            self.__command,
            self.__pic,
            self.checksum,
            uid,
            self.__options,
            *self.__data,
        )

    @classmethod
    def from_bytes(cls, raw_data: bytes):
        """
        Create a packet from bytes.

        Args:
          raw_data: Bytes representing the packet.

        Raises:
          ValueError: If the length of ``raw_data`` does not match ``Packet.SIZE``.

        Returns:
          Packet created from the bytes.
        """
        if len(raw_data) != Packet.SIZE:
            error = f"Packet size {len(raw_data)} does not match {Packet.SIZE}"
            raise ValueError(error)
        (
            command,
            pic,
            checksum,
            uid,
            options,
            *data,
        ) = struct.unpack(Packet.__bytes_fmt, raw_data)

        packet = cls()
        packet.with_command(command)
        packet.with_checksum(checksum)
        packet.with_pic(pic)
        packet.with_uid(uid)
        packet.with_options(options)
        packet.with_data(data)
        packet.craft()
        return packet

    def extract_sensors(self) -> Dict:
        """Extract the values of the sensors from the data.

        The information of the sensors is stored in the following way:

        #. ``temp_110_cal``: Calibration of temperature at 110 Celsius.
        #. ``temp_30_cal``: Calibration of temperature at 30 Celsius.
        #. ``temp_raw``: Raw value of temperature.
        #. ``vdd_cal``: Calibration of VDD.
        #. ``vdd_raw``: Raw value of VDD.

        All the values are stored in 2 bytes.

        Returns:
            Dictionary containing ``temperature`` and ``vdd``.
        """

        def calc_vdd(vdd: int, vdd_cal: int) -> float:
            """
            Calculate the working voltage.

            Args:
              vdd: Raw value from the voltage sensor.
              vdd_cal: Calibration value.

            Returns:
              The working vdd in volts.
            """
            return round((3300 * vdd_cal / vdd) * 0.001, 5)

        def calc_temp(temp: int, cal_30: int, cal_110: int) -> float:
            """
            Calculate the working temperature.

            Args:
              temp: Raw value from the temperature sensor.
              cal_30: Calibration value at 30 degrees celsius.
              cal_110: Calibration value at 110 degrees celsius.

            Returns:
              The working temperature in degrees celsius.
            """
            return round(((110 - 30) / (cal_110 - cal_30)) * (temp - cal_30) + 30.0, 5)

        data = struct.unpack("<HHHHH", bytes(self.__data[:10]))
        return {
            "temperature": calc_temp(data[2], data[1], data[0]),
            "voltage": calc_vdd(data[4], data[3]),
        }

    def to_bytes(self) -> bytes:
        """Return the bytes representation the packet.

        Returns:
            Bytes representation of the packet.

        Raises:
            ValueError if packet is not crafted.
        """
        if self.__bytes is None:
            raise ValueError("Packet is not crafted. Call craft() method first")
        return self.__bytes
