#!/usr/bin/env python3


class Reader:
    """Interface of a device reader.

    The reader acts as a proxy between the station and the devices.

    Attributes:
        name: Descriptive name of the reader.
    """

    def __init__(self, name: str):
        self.name = name

    def send(self, data: bytes):
        raise NotImplementedError

    def receive(self):
        raise NotImplementedError
