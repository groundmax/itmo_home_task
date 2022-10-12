import typing as tp
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TeamInfo(BaseModel):
    title: str
    chat_id: int
    api_base_url: str
    api_key: tp.Optional[str]


class Team(TeamInfo):
    team_id: UUID
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    team_id: UUID
    name: str
    description: tp.Optional[str]


class Model(ModelInfo):
    model_id: UUID
    created_at: datetime
