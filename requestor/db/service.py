from uuid import UUID
import typing as tp
from asyncpg import Pool, UniqueViolationError
from pydantic.main import BaseModel

from requestor.log import app_logger
from requestor.models import TeamInfo, Team
from requestor.utils import utc_now

from .exceptions import DuplicatedTeamError, TeamNotFoundError


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

    # async def add_obstrel(ObstrelInfo):
    #     pass
    #
    # async def set_obstrel_status(obstrel_id, status):
    #     pass
    #
    # async def add_model_metrics(obstrel_id, metrics):
    #     pass
