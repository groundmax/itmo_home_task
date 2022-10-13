import typing as tp
from uuid import UUID

from asyncpg import ForeignKeyViolationError, Pool, UniqueViolationError
from pydantic.main import BaseModel

from requestor.log import app_logger
from requestor.models import Model, ModelInfo, Team, TeamInfo, Trial, TrialStatus
from requestor.utils import utc_now

from .exceptions import (
    DuplicatedModelError,
    DuplicatedTeamError,
    ModelNotFoundError,
    TeamNotFoundError,
    TrialNotFoundError,
)


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

    async def add_team(self, team_info: TeamInfo) -> Team:
        query = """
            INSERT INTO teams
                (title, chat_id, api_base_url, api_key, created_at, updated_at)
            VALUES
                (
                    $1::VARCHAR
                    , $2::BIGINT
                    , $3::VARCHAR
                    , $4::VARCHAR
                    , $5::TIMESTAMP
                    , $6::TIMESTAMP
                )
            RETURNING
                team_id
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
                utc_now(),
            )
            return Team(**record)
        except UniqueViolationError as e:
            raise DuplicatedTeamError(e)

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

    async def get_team_by_chat(self, chat_id: int) -> tp.Optional[Team]:
        query = """
            SELECT *
            FROM teams
            WHERE chat_id = $1::BIGINT
        """
        record = await self.pool.fetchrow(query, chat_id)
        res = Team(**record) if record is not None else None
        return res

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

    async def get_team_models(self, team_id: UUID) -> tp.List[Model]:
        query = """
           SELECT *
           FROM models
           WHERE team_id = $1::UUID
        """
        records = await self.pool.fetch(query, team_id)
        return [Model(**record) for record in records]

    async def add_trial(self, model_id: UUID, status: TrialStatus) -> Trial:
        if status.is_finished():
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
            utc_now() if status.is_finished() else None,
            status,
            trial_id,
        )

        if record is None:
            raise TrialNotFoundError(f"Trial '{trial_id}' not found")
        return Trial(**record)

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

    # async def add_model_metrics(obstrel_id, metrics):
    #     pass
