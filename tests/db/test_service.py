# pylint: disable=attribute-defined-outside-init
from uuid import UUID, uuid4

import pytest
from sqlalchemy import orm

from requestor.db.exceptions import DuplicatedModelError, DuplicatedTeamError, TeamNotFoundError
from requestor.db.models import ModelsTable, TeamsTable
from requestor.db.service import DBService
from requestor.models import ModelInfo, TeamInfo
from requestor.utils import utc_now
from tests.utils import (
    ApproxDatetime,
    DBObjectCreator,
    assert_db_model_equal_to_pydantic_model,
    make_db_model,
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


class TestModels:
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

    @staticmethod
    def add_team(
        team_info: TeamInfo,
        create_db_object: DBObjectCreator,
    ) -> UUID:
        team_id = uuid4()
        create_db_object(make_db_team(**team_info.dict(), team_id=team_id))
        return team_id

    @staticmethod
    def make_model_info(team_id: UUID, rnd: str = "") -> ModelInfo:
        return ModelInfo(team_id=team_id, name=f"some_name_{rnd}", description=f"some_desc_{rnd}")

    async def test_add_model_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = self.add_team(self.team_info, create_db_object)
        model_info = self.make_model_info(team_id)

        model = await db_service.add_model(model_info)
        for field in ModelInfo.schema()["properties"].keys():
            assert getattr(model_info, field) == getattr(model, field)
        assert model.created_at == ApproxDatetime(utc_now())

        db_models = db_session.query(ModelsTable).all()
        assert len(db_models) == 1
        assert_db_model_equal_to_pydantic_model(db_models[0], model)

    async def test_add_duplicated_model(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = self.add_team(self.team_info, create_db_object)
        model_info = self.make_model_info(team_id)

        create_db_object(make_db_model(**model_info.dict()))

        other_model_info = model_info.copy()
        other_model_info.description = "other_description"
        with pytest.raises(DuplicatedModelError, match="team_id, name"):
            await db_service.add_model(other_model_info)
        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1

    async def test_add_model_for_nonexistent_team(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        model_info = self.make_model_info(uuid4())
        with pytest.raises(TeamNotFoundError):
            await db_service.add_model(model_info)

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 0

    async def test_get_team_models_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = self.add_team(self.team_info, create_db_object)
        model_1_info = self.make_model_info(team_id, rnd="1")
        create_db_object(make_db_model(**model_1_info.dict()))
        model_2_info = self.make_model_info(team_id, rnd="2")
        create_db_object(make_db_model(**model_2_info.dict()))

        models = await db_service.get_team_models(team_id)
        assert sorted(m.name for m in models) == [model_1_info.name, model_2_info.name]

    async def test_get_team_models_when_no_models(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = self.add_team(self.team_info, create_db_object)

        models = await db_service.get_team_models(team_id)
        assert len(models) == 0
