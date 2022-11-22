import functools
import typing as tp
from uuid import UUID

from asyncpg import (
    ConnectionDoesNotExistError,
    ForeignKeyViolationError,
    Pool,
    UniqueViolationError,
)
from pydantic.main import BaseModel

from requestor.log import app_logger
from requestor.models import (
    ByModelLeaderboardRow,
    GlobalLeaderboardRow,
    Metric,
    Model,
    ModelInfo,
    Team,
    TeamInfo,
    Trial,
    TrialStatus,
)
from requestor.utils import async_do_with_retries, utc_now

from ..settings import config
from .exceptions import (
    DuplicatedMetricError,
    DuplicatedModelError,
    DuplicatedTeamError,
    ModelNotFoundError,
    TeamNotFoundError,
    TokenNotFoundError,
    TrialNotFoundError,
)


def attempted(func: tp.Callable) -> tp.Callable:
    @functools.wraps(func)
    async def _wrapper(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
        res = await async_do_with_retries(
            func=func(*args, **kwargs),
            exc_type=(ConnectionRefusedError, ConnectionDoesNotExistError),
            max_attempts=config.db_config.n_attempts,
            interval=config.db_config.attempts_interval,
        )
        return res

    return _wrapper


class DBService(BaseModel):
    pool: Pool

    class Config:
        arbitrary_types_allowed = True

    async def setup(self) -> None:
        await self.pool
        app_logger.info("Db service initialized")

    async def cleanup(self) -> None:
        await self.pool.close()
        app_logger.info("Db service shutdown")

    async def ping(self) -> bool:
        return await self.pool.fetchval("SELECT TRUE")

    async def _remove_token(self, token: str) -> None:
        query = """
            DELETE FROM tokens
            WHERE token = $1::VARCHAR
            RETURNING team_description
        """
        team_description = await self.pool.fetchval(query, token)
        if team_description is None:
            raise TokenNotFoundError()

    async def _get_team_description_by_token(self, token: str) -> str:
        query = """
            SELECT team_description
            FROM tokens
            WHERE token = $1::VARCHAR
        """

        team_description = await self.pool.fetchval(query, token)

        if team_description is None:
            raise TokenNotFoundError()
        return team_description

    async def add_team(self, team_info: TeamInfo, token: str) -> Team:
        description = await self._get_team_description_by_token(token)
        query = """
            INSERT INTO teams
                (description, title, chat_id, api_base_url, api_key, created_at, updated_at)
            VALUES
                (
                    $1::VARCHAR
                    , $2::VARCHAR
                    , $3::BIGINT
                    , $4::VARCHAR
                    , $5::VARCHAR
                    , $6::TIMESTAMP
                    , $7::TIMESTAMP
                )
            RETURNING
                team_id
                , description
                , title
                , chat_id
                , api_base_url
                , api_key
                , created_at
                , updated_at
        """
        try:
            record = await self.pool.fetchrow(
                query,
                description,
                team_info.title,
                team_info.chat_id,
                team_info.api_base_url,
                team_info.api_key,
                utc_now(),
                utc_now(),
            )
            await self._remove_token(token)
            return Team(**record)
        except UniqueViolationError as e:
            raise DuplicatedTeamError(e)

    @attempted
    async def update_team(self, team_id: UUID, team_info: TeamInfo) -> Team:
        query = """
            UPDATE teams
            SET
                title = $1::VARCHAR
                , chat_id = $2::BIGINT
                , api_base_url = $3::VARCHAR
                , api_key = $4::VARCHAR
                , updated_at = $5::TIMESTAMP
            WHERE team_id = $6::UUID
            RETURNING
                team_id
                , description
                , title
                , chat_id
                , api_base_url
                , api_key
                , created_at
                , updated_at
        """
        try:
            record = await self.pool.fetchrow(
                query,
                team_info.title,
                team_info.chat_id,
                team_info.api_base_url,
                team_info.api_key,
                utc_now(),
                team_id,
            )
        except UniqueViolationError as e:
            raise DuplicatedTeamError(e)

        if record is None:
            raise TeamNotFoundError(f"Team '{team_id}' not found")
        return Team(**record)

    @attempted
    async def get_team_by_chat(self, chat_id: int) -> Team:
        query = """
            SELECT *
            FROM teams
            WHERE chat_id = $1::BIGINT
        """
        record = await self.pool.fetchrow(query, chat_id)

        if record is None:
            raise TeamNotFoundError()
        return Team(**record)

    @attempted
    async def add_model(self, model_info: ModelInfo) -> Model:
        query = """
            INSERT INTO models
                (team_id, name, description, created_at)
            VALUES
                (
                    $1::UUID
                    , $2::VARCHAR
                    , $3::VARCHAR
                    , $4::TIMESTAMP
                )
            RETURNING
                model_id
                , team_id
                , name
                , description
                , created_at
        """
        try:
            record = await self.pool.fetchrow(
                query,
                model_info.team_id,
                model_info.name,
                model_info.description,
                utc_now(),
            )
            return Model(**record)
        except UniqueViolationError as e:
            raise DuplicatedModelError(e)
        except ForeignKeyViolationError:
            raise TeamNotFoundError()

    @attempted
    async def get_team_last_n_models(self, team_id: UUID, limit: int) -> tp.List[Model]:
        if limit <= 0:
            raise ValueError(f"Parameter 'limit' should be positive, but got: {limit}")
        query = """
           SELECT *
           FROM models
           WHERE team_id = $1::UUID
           ORDER BY created_at DESC
           LIMIT $2::BIGINT
        """
        records = await self.pool.fetch(query, team_id, limit)
        return [Model(**record) for record in records]

    @attempted
    async def get_model_by_name(self, team_id: UUID, model_name: str) -> Model:
        query = """
            SELECT *
            FROM models
            where team_id = $1::UUID and name = $2::VARCHAR
        """
        record = await self.pool.fetchrow(query, team_id, model_name)
        if record is None:
            raise ModelNotFoundError(f"Model {model_name} not found")

        return Model(**record)

    @attempted
    async def add_trial(self, model_id: UUID, status: TrialStatus) -> Trial:
        if status.is_finished:
            raise ValueError("New trial cannot be finished")

        query = """
            INSERT INTO trials
                (model_id, created_at, status)
            VALUES
                (
                    $1::UUID
                    , $2::TIMESTAMP
                    , $3::trial_status_enum
                )
            RETURNING
                trial_id
                , model_id
                , created_at
                , finished_at
                , status
        """
        try:
            record = await self.pool.fetchrow(
                query,
                model_id,
                utc_now(),
                status,
            )
        except ForeignKeyViolationError:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return Trial(**record)

    @attempted
    async def update_trial_status(self, trial_id: UUID, status: TrialStatus) -> Trial:
        query = """
            UPDATE trials
            SET
                finished_at = $1::TIMESTAMP
                , status = $2::trial_status_enum
            WHERE trial_id = $3::UUID
            RETURNING
                trial_id
                , model_id
                , created_at
                , finished_at
                , status
        """
        record = await self.pool.fetchrow(
            query,
            utc_now() if status.is_finished else None,
            status,
            trial_id,
        )

        if record is None:
            raise TrialNotFoundError(f"Trial '{trial_id}' not found")
        return Trial(**record)

    @attempted
    async def get_team_today_trial_stat(self, team_id: UUID) -> tp.Dict[TrialStatus, int]:
        query = """
            SELECT status, count(*) AS n_trials
            FROM trials t
                JOIN models m on t.model_id = m.model_id
            WHERE m.team_id = $1::UUID and t.created_at::DATE = $2::DATE
            GROUP BY status
        """
        records = await self.pool.fetch(query, team_id, utc_now().date())
        return {r["status"]: r["n_trials"] for r in records}

    @attempted
    async def add_metrics(self, trial_id: UUID, metrics: tp.Iterable[Metric]) -> None:
        query = """
            INSERT INTO metrics
                (trial_id, name, value)
            VALUES
                (
                    $1::UUID
                    , $2::VARCHAR
                    , $3::FLOAT
                )
        """
        values = ((trial_id, m.name, m.value) for m in metrics)
        try:
            await self.pool.executemany(query, values)
        except UniqueViolationError as e:
            raise DuplicatedMetricError(e)
        except ForeignKeyViolationError:
            raise TrialNotFoundError()

    @attempted
    async def get_global_leaderboard(self, metric: str) -> tp.List[GlobalLeaderboardRow]:
        query = """
            WITH trials_stat AS (
                SELECT m.team_id, COUNT(*) AS n_attempts, MAX(t.created_at) AS last_attempt
                FROM models m
                    JOIN trials t on m.model_id = t.model_id
                WHERE t.status = 'success'
                GROUP BY m.team_id
            ),
            best_metrics AS (
                SELECT m.team_id, MAX(me.value) AS best_score
                FROM models m
                    JOIN trials tr on m.model_id = tr.model_id
                    JOIN metrics me on tr.trial_id = me.trial_id
                WHERE me.name = $1::VARCHAR
                GROUP BY m.team_id
            )
            SELECT
                t.description AS team_name
                , best_score
                , COALESCE(n_attempts, 0) AS n_attempts
                , last_attempt
            FROM teams t
                LEFT JOIN trials_stat ts on t.team_id = ts.team_id
                LEFT JOIN best_metrics bm on t.team_id = bm.team_id
            ORDER BY best_score DESC NULLS LAST, last_attempt ASC NULLS LAST, t.description ASC
        """
        records = await self.pool.fetch(query, metric)
        return [GlobalLeaderboardRow(**record) for record in records]

    @attempted
    async def get_by_model_leaderboard(self, metric: str) -> tp.List[ByModelLeaderboardRow]:
        query = """
            SELECT
                t.description AS team_name
                , m.name AS model_name
                , MAX(me.value) AS best_score
                , COUNT(*) AS n_attempts
                , MAX(tr.created_at) AS last_attempt
            FROM teams t
                JOIN models m on t.team_id = m.team_id
                JOIN trials tr on m.model_id = tr.model_id
                JOIN metrics me on tr.trial_id = me.trial_id
            WHERE tr.status = 'success' AND me.name = $1::VARCHAR
            GROUP BY t.description, m.name
            ORDER BY t.description, m.name
        """
        records = await self.pool.fetch(query, metric)
        return [ByModelLeaderboardRow(**record) for record in records]
