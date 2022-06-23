#!/usr/bin/env python3
import struct
from typing import Dict, List, Optional, Union
from enum import Enum


class Method(Enum):
    #: Packet has been received correctly.
    ACK = 1
    #: Identify devices in a chain.
    PING = 2
    #: Read a region of memory.
    READ = 3
    #: Write to a region of memory.
    WRITE = 4
    #: Read the sensors of a device.
    SENSORS = 5
    #: Execute custom code on a device.
    EXEC = 6
    #: Error when receiveng a packet.
    ERR = 255


class Packet:
    """Packet used for the communication protocol.

    Attributes:
        method:
        pic:
        options:
        uid:
        checksum:
        data:
        bytes:
    """

    #: How many bytes of data the packet holds.
    DATA_SIZE = 512
    __bytes_fmt = f"<BBH25sI{DATA_SIZE}B"
    #: Total size of the packet.
    SIZE = struct.calcsize(__bytes_fmt)

    def __init__(self):
        self.__method: int = Method.PING.value
        self.__pic: int = 0
        self.__options: int = 0x0
        self.__uid: str = "0" * 24
        self.__data: List[int] = [0x7] * Packet.DATA_SIZE
        self.__bytes: Optional[bytes] = None
        self.checksum: Optional[int] = None

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

    def with_method(self, method: Union[int, Method]):
        """Set the method of the packet."""
        if isinstance(method, Method):
            self.__method = method.value
        else:
            self.__method = method

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
        if self.checksum is None:
            self.__bytes = struct.pack(
                self.__bytes_fmt,
                self.__method,
                self.__pic,
                0,
                bytes(self.__uid, "utf-8"),
                self.__options,
                *self.__data,
            )
            self.checksum = sum(bytearray(self.__bytes)) % 0xFFFF
        self.__bytes = struct.pack(
            self.__bytes_fmt,
            self.__method,
            self.__pic,
            self.checksum,
            bytes(self.__uid, "utf-8"),
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
            method,
            pic,
            checksum,
            uid,
            options,
            *data,
        ) = struct.unpack(Packet.__bytes_fmt, raw_data)

        packet = cls()
        packet.with_method(method)
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
        """
        if self.__bytes is None:
            raise ValueError("Packet is not crafted.")
        else:
            return self.__bytes
