#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Any, Optional, Union, Type

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta

# Base object used to create classes for storage
TableBase = declarative_base()


@dataclass
class DBParameters:
    """Class to manage database connection parameters.

    By default it is assumed that the database is PostgreSQL.
    For a list of supported engines, please see `https://docs.sqlalchemy.org/en/14/core/engines.html`.

    Attributes:
        user: Username to connect to the database.
        password: User password to connect to the database.
        dbname: Name of the database to connect.
        engine: Database to use. Defaults to 'postgresql'.
        host: Hostname for the database. Defaults to 'localhost'.
        port: Connection port for the database. Defaults to 5432.
    """

    user: str
    password: str
    dbname: Optional[str] = None
    engine: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None

    def __post_init__(self):
        if self.engine is None:
            self.engine = "postgresql"
        if self.host is None:
            self.host = "localhost"
        if self.port is None:
            self.port = 5432

    def __str__(self):
        return (
            f"{self.engine}://"
            f"{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )


class DBManager:
    """Class to manage the communication with the database.

    The default database is PostreSQL. However, another database can be used in place by configuring the DBManager.

    The manager is allowed to insert into the database any object as long as it has been registered by using ``TableBase``.  For more instructions on how to register objects to the database please see `https://docs.sqlalchemy.org/en/14/orm/declarative_tables.html`.

    Example:
        >>> from sramplatform.storage import DBManager, TableBase
        >>>
        >>> class Users(TableBase):
        >>>     __tablename__ = "User"
        >>>     id = Column(Integer, primary_key=True)
        >>>     name = Column(String, nullable=False)
        >>>
        >>> manager = DBManager(url)

    Queries can be made by using the session attribute.
    Example:
        >>> manager.session.query(User).all

    Attributes:
        session: Session to the DB

    Args:
        url: DBParameters instance or string containing the url to connect.
    """

    def __init__(self, url: Union[str, DBParameters]):
        engine = create_engine(str(url))

        Session = sessionmaker(engine)
        self.session = Session()
        TableBase.metadata.create_all(engine)

    def insert(self, data: object):
        """Insert an item into the DB.

        Args:
            data: Data to be inserted in the database.
        """
        self.session.add(data)

    def commit(self):
        """Commit the pending changes to the DB."""
        self.session.commit()
