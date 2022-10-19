import typing as tp
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class TokenInfo(BaseModel):
    token: str
    team_description: str


class TeamInfo(BaseModel):
    title: str
    chat_id: int
    api_base_url: str
    api_key: tp.Optional[str]


class Team(TeamInfo):
    team_id: UUID
    description: str
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    team_id: UUID
    name: str
    description: tp.Optional[str]


class Model(ModelInfo):
    model_id: UUID
    created_at: datetime


class TrialStatus(str, Enum):
    waiting = "waiting"
    started = "started"
    success = "success"
    failed = "failed"

    @property
    def is_finished(self) -> bool:
        return self.value in (self.success, self.failed)


class Trial(BaseModel):
    trial_id: UUID
    model_id: UUID
    created_at: datetime
    finished_at: tp.Optional[datetime]
    status: TrialStatus


class Metric(BaseModel):
    name: str
    value: float
