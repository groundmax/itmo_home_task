# pylint: disable=attribute-defined-outside-init
from uuid import uuid4

import pytest
from sqlalchemy import orm

from requestor.db.exceptions import DuplicatedTeamError, TeamNotFoundError
from requestor.db.models import TeamsTable
from requestor.db.service import DBService
from requestor.models import TeamInfo
from requestor.utils import utc_now
from tests.utils import (
    ApproxDatetime,
    DBObjectCreator,
    assert_db_model_equal_to_pydantic_model,
    make_db_team,
)

pytestmark = pytest.mark.asyncio


async def test_ping(db_service: DBService) -> None:
    assert await db_service.ping()


class TestTeams:
    def setup(self) -> None:
        self.team_info = TeamInfo(
            title="some_title",
            chat_id=12345,
            api_base_url="some_url",
            api_key="some_key",
        )
        self.other_team_info = TeamInfo(
            title="other_title",
            chat_id=54321,
            api_base_url="other_url",
            api_key=None,
        )

    async def test_add_team_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
    ) -> None:
        team = await db_service.add_team(self.team_info)
        for field in TeamInfo.schema()["properties"].keys():
            assert getattr(self.team_info, field) == getattr(team, field)
        assert team.created_at == ApproxDatetime(utc_now())
        assert team.updated_at == ApproxDatetime(utc_now())

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1
        db_team = db_teams[0]
        assert_db_model_equal_to_pydantic_model(db_team, team)

    @pytest.mark.parametrize("column", ("title", "chat_id", "api_base_url"))
    async def test_add_duplicated_team(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        column: str,
    ) -> None:
        create_db_object(make_db_team(**self.team_info.dict()))

        other_team_info = self.other_team_info
        setattr(other_team_info, column, getattr(self.team_info, column))
        with pytest.raises(DuplicatedTeamError, match=column):
            await db_service.add_team(other_team_info)
        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1

    async def test_update_team_success(
        self, db_service: DBService, db_session: orm.Session, create_db_object: DBObjectCreator
    ) -> None:
        team_id = uuid4()
        base_db_team = make_db_team(**self.team_info.dict(), team_id=team_id)
        create_db_object(base_db_team)
        updated_team = await db_service.update_team(team_id, self.other_team_info)
        for field in TeamInfo.schema()["properties"].keys():
            assert getattr(self.other_team_info, field) == getattr(updated_team, field)
        assert updated_team.updated_at == ApproxDatetime(utc_now())
        assert updated_team.created_at == base_db_team.created_at

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1
        db_team = db_teams[0]
        assert_db_model_equal_to_pydantic_model(db_team, updated_team)

    @pytest.mark.parametrize("column", ("title", "chat_id", "api_base_url"))
    async def test_update_team_with_duplicated_info(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        column: str,
    ) -> None:
        create_db_object(make_db_team(**self.team_info.dict()))

        team_id = uuid4()
        base_db_team = make_db_team(**self.other_team_info.dict(), team_id=team_id)
        create_db_object(base_db_team)

        updated_team_info = self.other_team_info
        setattr(updated_team_info, column, getattr(self.team_info, column))
        with pytest.raises(DuplicatedTeamError, match=column):
            await db_service.update_team(team_id, updated_team_info)

    async def test_update_nonexistent_team(self, db_service: DBService) -> None:
        with pytest.raises(TeamNotFoundError):
            await db_service.update_team(uuid4(), self.other_team_info)

    async def test_get_team_by_chat_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        db_team = make_db_team(**self.team_info.dict())
        create_db_object(db_team)
        team = await db_service.get_team_by_chat(self.team_info.chat_id)
        assert_db_model_equal_to_pydantic_model(db_team, team)

    async def test_get_nonexistent_team_by_chat_success(self, db_service: DBService) -> None:
        team = await db_service.get_team_by_chat(self.team_info.chat_id)
        assert team is None
