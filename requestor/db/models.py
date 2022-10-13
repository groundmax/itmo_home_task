from sqlalchemy import Column, ForeignKey, Index, orm
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from requestor.models import TrialStatus
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


trial_status_enum = pg.ENUM(
    *TrialStatus.__members__.keys(),
    name="trial_status_enum",
    create_type=False,
)


class TrialsTable(Base):
    __tablename__ = "trials"

    trial_id = Column(pg.UUID, primary_key=True, default=make_uuid)
    model_id = Column(pg.UUID, ForeignKey(ModelsTable.model_id), nullable=False)
    created_at = Column(pg.TIMESTAMP, nullable=False)
    finished_at = Column(pg.TIMESTAMP, nullable=True)
    status = Column(trial_status_enum, nullable=False)

    model = orm.relationship(ModelsTable)


class MetricsTable(Base):
    __tablename__ = "metrics"

    trial_id = Column(pg.UUID, ForeignKey(TrialsTable.trial_id), primary_key=True)
    name = Column(pg.VARCHAR(64), primary_key=True)
    value = Column(pg.FLOAT, nullable=False)
