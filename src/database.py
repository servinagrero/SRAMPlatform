#!/usr/bin/env python3

from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from sramplatform.storage import DBManager, DBParameters, TableBase


class Sample(TableBase):
    __tablename__ = "CRP"
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


class Sensor(TableBase):
    __tablename__ = "Sensor"
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


params = DBParameters("user", "password", "database")
dbmanager = DBManager(params)
