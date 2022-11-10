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


def offset_to_address(offset: int, data_size: int, sram_start: int = 0x20000000) -> str:
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

    return f"0x{sram_start + (offset * data_size):08X}"


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

    def __init__(self, data_size: int):
        self.data_size = data_size
        self.bytes_fmt = f"<BBI25s{self.data_size}BH"
        self.size = struct.calcsize(self.bytes_fmt)

        self.__command: int = Command.PING.value
        self.__pic: int = 0
        self.__options: int = 0x0
        self.__uid: str = "0" * 25
        self.__data: List[int] = [0x7] * self.data_size
        self.checksum: Optional[int] = None
        self.__bytes: Optional[bytes] = None

    @classmethod
    def full_size(cls, data_size: int):
        packet = cls(data_size)
        return packet.size

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
                self.bytes_fmt,
                self.__command,
                self.__pic,
                self.__options,
                uid,
                *self.__data,
                0,
            )
            self.checksum = crc16(self.__bytes)
        self.__bytes = struct.pack(
            self.bytes_fmt,
            self.__command,
            self.__pic,
            self.__options,
            uid,
            *self.__data,
            self.checksum,
        )

    @classmethod
    def from_bytes(cls, data_size: int, raw_data: bytes):
        """
        Create a packet from bytes.

        Args:
          raw_data: Bytes representing the packet.

        Raises:
          ValueError: If the length of ``raw_data`` does not match ``Packet.SIZE``.

        Returns:
          Packet created from the bytes.
        """
        packet = cls(data_size)

        if len(raw_data) != packet.size:
            error = f"Packet size {len(raw_data)} does not match {data_size}"
            raise ValueError(error)
        (
            command,
            pic,
            options,
            uid,
            *data,
            checksum,
        ) = struct.unpack(packet.bytes_fmt, raw_data)

        packet.with_command(command)
        packet.with_pic(pic)
        packet.with_uid(uid)
        packet.with_options(options)
        packet.with_data(data)
        packet.with_checksum(checksum)
        packet.craft()
        return packet

    def extract_sensors(self) -> Dict:
        """Extract the values of the sensors from the data.

        The information of the sensors is stored in the following way:

        - `temp_110_cal`: Temperature calibration at 110 Celsius.
        - `temp_30_cal`: Temperature calibration at 30 Celsius.
        - `temp_raw`: Raw value of temperature.
        - `vdd_cal`: Calibration of VDD.
        - `vdd_raw`: Raw value of VDD.

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

    def check_crc(self) -> bool:
        if self.__bytes is None:
            raise ValueError("Packet is not crafted. Call craft() method first")
        buffer = bytearray(self.__bytes)
        buffer[-1], buffer[-2] = 0, 0
        return crc16(buffer) == self.checksum


# Extracted from: https://www.devcoons.com/crc16-simple-algorithm-c/
CRC16_LUT = [
    0x0000,
    0xC0C1,
    0xC181,
    0x0140,
    0xC301,
    0x03C0,
    0x0280,
    0xC241,
    0xC601,
    0x06C0,
    0x0780,
    0xC741,
    0x0500,
    0xC5C1,
    0xC481,
    0x0440,
    0xCC01,
    0x0CC0,
    0x0D80,
    0xCD41,
    0x0F00,
    0xCFC1,
    0xCE81,
    0x0E40,
    0x0A00,
    0xCAC1,
    0xCB81,
    0x0B40,
    0xC901,
    0x09C0,
    0x0880,
    0xC841,
    0xD801,
    0x18C0,
    0x1980,
    0xD941,
    0x1B00,
    0xDBC1,
    0xDA81,
    0x1A40,
    0x1E00,
    0xDEC1,
    0xDF81,
    0x1F40,
    0xDD01,
    0x1DC0,
    0x1C80,
    0xDC41,
    0x1400,
    0xD4C1,
    0xD581,
    0x1540,
    0xD701,
    0x17C0,
    0x1680,
    0xD641,
    0xD201,
    0x12C0,
    0x1380,
    0xD341,
    0x1100,
    0xD1C1,
    0xD081,
    0x1040,
    0xF001,
    0x30C0,
    0x3180,
    0xF141,
    0x3300,
    0xF3C1,
    0xF281,
    0x3240,
    0x3600,
    0xF6C1,
    0xF781,
    0x3740,
    0xF501,
    0x35C0,
    0x3480,
    0xF441,
    0x3C00,
    0xFCC1,
    0xFD81,
    0x3D40,
    0xFF01,
    0x3FC0,
    0x3E80,
    0xFE41,
    0xFA01,
    0x3AC0,
    0x3B80,
    0xFB41,
    0x3900,
    0xF9C1,
    0xF881,
    0x3840,
    0x2800,
    0xE8C1,
    0xE981,
    0x2940,
    0xEB01,
    0x2BC0,
    0x2A80,
    0xEA41,
    0xEE01,
    0x2EC0,
    0x2F80,
    0xEF41,
    0x2D00,
    0xEDC1,
    0xEC81,
    0x2C40,
    0xE401,
    0x24C0,
    0x2580,
    0xE541,
    0x2700,
    0xE7C1,
    0xE681,
    0x2640,
    0x2200,
    0xE2C1,
    0xE381,
    0x2340,
    0xE101,
    0x21C0,
    0x2080,
    0xE041,
    0xA001,
    0x60C0,
    0x6180,
    0xA141,
    0x6300,
    0xA3C1,
    0xA281,
    0x6240,
    0x6600,
    0xA6C1,
    0xA781,
    0x6740,
    0xA501,
    0x65C0,
    0x6480,
    0xA441,
    0x6C00,
    0xACC1,
    0xAD81,
    0x6D40,
    0xAF01,
    0x6FC0,
    0x6E80,
    0xAE41,
    0xAA01,
    0x6AC0,
    0x6B80,
    0xAB41,
    0x6900,
    0xA9C1,
    0xA881,
    0x6840,
    0x7800,
    0xB8C1,
    0xB981,
    0x7940,
    0xBB01,
    0x7BC0,
    0x7A80,
    0xBA41,
    0xBE01,
    0x7EC0,
    0x7F80,
    0xBF41,
    0x7D00,
    0xBDC1,
    0xBC81,
    0x7C40,
    0xB401,
    0x74C0,
    0x7580,
    0xB541,
    0x7700,
    0xB7C1,
    0xB681,
    0x7640,
    0x7200,
    0xB2C1,
    0xB381,
    0x7340,
    0xB101,
    0x71C0,
    0x7080,
    0xB041,
    0x5000,
    0x90C1,
    0x9181,
    0x5140,
    0x9301,
    0x53C0,
    0x5280,
    0x9241,
    0x9601,
    0x56C0,
    0x5780,
    0x9741,
    0x5500,
    0x95C1,
    0x9481,
    0x5440,
    0x9C01,
    0x5CC0,
    0x5D80,
    0x9D41,
    0x5F00,
    0x9FC1,
    0x9E81,
    0x5E40,
    0x5A00,
    0x9AC1,
    0x9B81,
    0x5B40,
    0x9901,
    0x59C0,
    0x5880,
    0x9841,
    0x8801,
    0x48C0,
    0x4980,
    0x8941,
    0x4B00,
    0x8BC1,
    0x8A81,
    0x4A40,
    0x4E00,
    0x8EC1,
    0x8F81,
    0x4F40,
    0x8D01,
    0x4DC0,
    0x4C80,
    0x8C41,
    0x4400,
    0x84C1,
    0x8581,
    0x4540,
    0x8701,
    0x47C0,
    0x4680,
    0x8641,
    0x8201,
    0x42C0,
    0x4380,
    0x8341,
    0x4100,
    0x81C1,
    0x8081,
    0x4040,
]


def crc16(buffer: bytes) -> int:
    """Calculate the CRC16 from a byte buffer.
    
    Args:
        buffer: Buffer of bytes.
    
    Returns:
        The calculated CRC.
    """
    crc = 0

    def crc16_byte(crc, data):
        """Helper function to get a value from the CRC16_LUT"""
        return (crc >> 8) ^ CRC16_LUT[(crc ^ data) & 0xFF]

    for byte in buffer:
        crc = crc16_byte(crc, byte)
    return crc
