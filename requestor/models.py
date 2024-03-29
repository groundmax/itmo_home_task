import asyncio
import typing as tp
from datetime import datetime
from enum import Enum
from uuid import UUID

from aiogram import types
from aiogram.utils.exceptions import RetryAfter
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module


class TokenInfo(BaseModel):
    token: str
    team_description: str


class TeamInfo(BaseModel):
    chat_id: int
    api_base_url: str = Field(max_length=256)
    api_key: tp.Optional[str] = Field(max_length=128)


class Team(TeamInfo):
    team_id: UUID
    description: str
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    team_id: UUID
    name: str = Field(max_length=64)
    description: tp.Optional[str] = Field(max_length=256)


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


class GlobalLeaderboardRow(BaseModel):
    team_name: str
    best_score: tp.Optional[float]
    n_attempts: int
    last_attempt: tp.Optional[datetime]


class ByModelLeaderboardRow(BaseModel):
    team_name: str
    model_name: str
    best_score: float
    n_attempts: int
    last_attempt: datetime


class ProgressNotifier(BaseModel):
    message: types.Message

    async def send_progress_update(self, info: str) -> None:
        try:
            await self.message.edit_text(info)
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await self.send_progress_update(info)

    async def reply(self, info: str) -> None:
        try:
            await self.message.reply(info)
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await self.reply(info)

    class Config:
        arbitrary_types_allowed = True
