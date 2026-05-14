from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

SCHEMA = "macrohero_new"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)
