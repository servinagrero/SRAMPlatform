#!/usr/bin/env python3

import os
from typing import Union
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class Log(Base):
    """Log every operation carried out by a station."""

    __tablename__ = "log"
    #: Internal id of the log.
    id = Column(Integer, primary_key=True)
    #: Name of the Reader to log.
    node = Column(String, nullable=False)
    #: Severity level of the message.
    status = Column(String, nullable=False)
    #: Descriptive text of the operation or information.
    message = Column(String, nullable=False)
    #: Timestamp when the operation was carried out.
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Sample(Base):
    __tablename__ = "sample"
    #: Internal id of the sample.
    id = Column(Integer, primary_key=True)
    #: Type of device connected in the chain.
    board_id = Column(String, nullable=False)
    #: Universal ID of the device.
    uid = Column(String, nullable=False)
    #: Position In Chain of the device.
    pic = Column(Integer, nullable=False)
    #: Region of SRAM. Formated as 0x00000000
    address = Column(String, nullable=False)
    #: Comma separated list of values from the memory.
    data = Column(String, nullable=False)
    #: Timestamp when the sample was gathered.
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Sensor(Base):
    __tablename__ = "sensor"
    #: Internal id of the sensor data.
    id = Column(Integer, primary_key=True)
    #: Type of device connected in the chain.
    board_id = Column(String, nullable=False)
    #: Universal ID of the device.
    uid = Column(String, nullable=False)
    #: Temperature value in degrees celsius.
    temperature = Column(Float, nullable=False)
    #: Internal VDD in volts.
    voltage = Column(Float, nullable=False)
    #: Timestamp when the sensor data was obtained.
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


#: Severity level of a log
class LogLevel(Enum):
    Info = "INFO"
    Warning = "WARNING"
    Critical = "CRITICAL"


class DBManager:
    """Class to manage the communication with the PostgreSQL database.

    Attributes:
        session: Session to the DB
    """

    def __init__(self, url):
        # postgres://username:password@localhost:5432/database
        engine = create_engine(url)

        Session = sessionmaker(engine)
        self.session = Session()
        Base.metadata.create_all(engine)

    def log(self, node: str, level: LogLevel, message: str):
        """Wrapper to store a log in the DB.

        Args:
            node: Name of the reader.
            level: Severity level of the log.
            message: Information to log in the DB.
        """
        self.session.add(Log(node=node, status=level.value, message=message))
        self.session.commit()

    def insert(self, data: Union[Sample, Sensor]):
        """Insert an item into the DB.

        The method can be used to insert both a Sample or a Sensor.

        Args:
            data: Data to be inserted in the database.
        """
        self.session.add(data)

    def commit(self):
        """Commit the pending changes to the DB."""
        self.session.commit()
