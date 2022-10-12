from sqlalchemy import Column, ForeignKey, Index, orm
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from requestor.utils import make_uuid

Base: DeclarativeMeta = declarative_base()


class TeamsTable(Base):
    __tablename__ = "teams"

    team_id = Column(pg.UUID, primary_key=True, default=make_uuid)
    title = Column(pg.VARCHAR(128), nullable=False, unique=True)
    chat_id = Column(pg.BIGINT, nullable=False, unique=True, index=True)
    api_base_url = Column(pg.VARCHAR(256), nullable=False, unique=True)
    api_key = Column(pg.VARCHAR(128), nullable=True)
    created_at = Column(pg.TIMESTAMP, nullable=False)
    updated_at = Column(pg.TIMESTAMP, nullable=False)


class ModelsTable(Base):
    __tablename__ = "models"

    model_id = Column(pg.UUID, primary_key=True, default=make_uuid)
    team_id = Column(pg.UUID, ForeignKey(TeamsTable.team_id), nullable=False)
    name = Column(pg.VARCHAR(64), nullable=False)
    description = Column(pg.VARCHAR(256), nullable=True)
    created_at = Column(pg.TIMESTAMP, nullable=False)

    team = orm.relationship(TeamsTable)

    __table_args__ = (Index("team_model_idx", "team_id", "name", unique=True),)
