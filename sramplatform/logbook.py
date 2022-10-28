#!/usr/bin/env python

import logging
from logging import FileHandler, StreamHandler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import sys
from typing import Dict, Any, TypeVar
from enum import Enum

from fenneq import Sender
from telebot import TeleBot
import yagmail
import yaml


HandlerType = TypeVar("HandlerType")

# Create a custom level to log command results
RESULTS_LEVEL = logging.CRITICAL + 10
logging.addLevelName(RESULTS_LEVEL, "RESULTS")
logging.RESULTS = logging.CRITICAL + 10


def results(self, message, *args, **kws):
    if self.isEnabledFor(RESULTS_LEVEL):
        self._log(RESULTS_LEVEL, message, args, **kws)


logging.Logger.results = results


def make_formatter(conf: Dict[str, str], fmt_default: str, datefmt_default: str):
    """Create a Log formatter from a dict.

    Args:
        conf: Dictionary containing format and datefmt
        fmt_default: Default format to use if none specified.
        datefmt_default: Default datefmt to use if none specified.
    """
    return logging.Formatter(
        conf.get("format", fmt_default),
        datefmt=conf.get("datefmt", datefmt_default),
    )


def create_handler(name: str, conf: Dict[str, Any]) -> HandlerType:
    """Create a handler from a name and a dict.

    Args:
        name: Name of the handler to create.
        conf: Dictionary containing the handler configuration.

    Returns:
        The configured handler.
    """
    if name == "TelegramHandler":
        return TelegramHandler(conf["token"], conf["chat_ids"])
    if name == "RabbitMQHandler":
        return RabbitMQHandler(conf["url"], conf["key"], conf["exachange"])
    if name == "MailHandler":
        return MailHandler(
            conf["mail"], conf["oauth"], conf["recipients"], conf["subject"]
        )
    if name == "FileHandler":
        return FileHandler(conf["path"])
    if name == "StreamHandler":
        return StreamHandler(sys.stdout)
    if name == "RotatingFileHandler":
        return RotatingFileHandler(
            conf["path"], maxBytes=conf["maxBytes"], backupCount=conf["backupCount"]
        )
    if name == "TimedRotatingFileHandler":
        return TimedRotatingFileHandler(
            conf["path"],
            when=conf["when"],
            backupCount=conf["backupCount"],
        )
    raise ValueError(f"Handler {name} is not available")


class CommandError(Exception):
    def __init__(self, msg, level=None):
        super().__init__(msg)
        self.level = level


class LogLevelFilter(logging.Filter):
    """https://stackoverflow.com/a/7447596/190597 (robert)"""

    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


class TelegramHandler(logging.StreamHandler):
    """Log handler for Telegram."""

    def __init__(self, token, chat_ids):
        super(TelegramHandler, self).__init__(self)
        self.bot = TeleBot(token)
        if isinstance(chat_ids, list):
            self.chat_ids = chat_ids
        else:
            self.chat_ids = [chat_ids]

    def emit(self, record):
        msg = self.format(record)
        for chat in self.chat_ids:
            self.bot.send_message(chat, msg)


class RabbitMQHandler(logging.StreamHandler):
    """Log handler for RabbitMQ."""

    def __init__(self, url, name, exchange):
        super(RabbitMQHandler, self).__init__(self)
        self.agent = Sender(url, name, exchange)

    def emit(self, record):
        msg = self.format(record)
        self.agent.send(msg)


class MailHandler(logging.StreamHandler):
    """Log handler for Email."""

    def __init__(self, email, oauth_path, recipients, subject):
        super(MailHandler, self).__init__(self)
        self.mail = yagmail.SMTP(email, oauth2_file=oauth_path)
        if isinstance(recipients, list):
            self.recipients = recipients
        else:
            self.recipients = list(recipients)
        self.subject = subject

    def emit(self, record):
        msg = self.format(record)
        template = f"""
        {msg}
        """
        self.mail.send(to=self.recipients, subject=self.subject, contents=template)
