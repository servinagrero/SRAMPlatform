#!/usr/bin/env python3

from typing import Union
from enum import Enum
import logging
from typing import Optional, Dict, Any, TypeVar, Tuple
import yaml
from dataclasses import dataclass

from fenneq import Agent

from sramplatform.reader import Reader
from sramplatform.logbook import Status, make_formatter, create_handler, LogLevelFilter

ReaderType = TypeVar("ReaderType", bound=Reader)


class Dispatcher:
    """Class used to dispatch reader methods based on the commands received.

    Attributes:
        agent: Fenneq agent to listen for commands.
        logger: Logger used to log information.
        db_session: Session to a DB to store data.
    """

    def __init__(self, agent, logger, db_session):
        self.agent = agent
        self.db_session = db_session
        self.logger = logger

    def add_command(self, handler, func, **options):
        """ """

        @self.agent.on(handler, **options)
        def handler_fn(msg):
            command = msg.body["command"]
            self.logger.debug("Handler %s called", command)
            try:
                res = func(msg.body, self.logger, self.db_session)
                if res == Status.OK:
                    self.logger.debug("Handler %s executed correctly", command)
                else:
                    self.logger.debug("Handler %s executed with errors", command)
            except Exception as excep:
                self.logger.critical(f"Error while executing handler: {excep}")

    def run(self):
        """Make the dispatcher listen for commands."""
        self.logger.debug(f"{self.agent.name} listening on {self.agent.exchange}")
        self.agent.run()


def from_config(
    config_path: str, reader_cls: ReaderType
) -> Tuple[Agent, ReaderType, object]:
    """Read a YAML config to generate the components for a Dispatcher.
    Args:
        config_path: Path to the YAML config.
        reader_cls: Class to use to instanciate a Reader.

    Returns:
        A tuple containing the Agent, Reader and Logger
    """
    with open(config_path, "r") as f:
        config = yaml.load(f, Loader=yaml.Loader)
        agent = Agent(**config["agent"])
        reader = reader_cls(**config["reader"])

        root_logger = logging.getLogger(agent.name)
        root_logger.setLevel(logging.DEBUG)
        conf_logging = config["logging"]

        fmt_default = conf_logging["format"]
        datefmt_default = conf_logging["datefmt"]

        for logger_conf in conf_logging.get("loggers", []):
            for name, conf in logger_conf.items():
                handler = create_handler(name, conf)
                level = logging.getLevelName(conf.get("level", logging.INFO))
                handler.setLevel(level)
                filter_level = conf.get("filter_level", None)
                if filter_level:
                    handler.addFilter(
                        LogLevelFilter(logging.getLevelName(filter_level))
                    )
                custom_fmt = make_formatter(conf, fmt_default, datefmt_default)
                handler.setFormatter(custom_fmt)
                root_logger.addHandler(handler)
    return agent, reader, root_logger
