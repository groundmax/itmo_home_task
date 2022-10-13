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
    OTHER_TEAM_INFO,
    TEAM_INFO,
    ApproxDatetime,
    DBObjectCreator,
    add_model,
    add_team,
    assert_db_model_equal_to_pydantic_model,
    gen_model_info,
    make_db_model,
    make_db_team,
)

pytestmark = pytest.mark.asyncio


async def test_ping(db_service: DBService) -> None:
    assert await db_service.ping()


class TestTeams:
    async def test_add_team_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
    ) -> None:
        team = await db_service.add_team(TEAM_INFO)
        for field in TeamInfo.schema()["properties"].keys():
            assert getattr(TEAM_INFO, field) == getattr(team, field)
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
        create_db_object(make_db_team(**TEAM_INFO.dict()))

        other_team_info = OTHER_TEAM_INFO.copy()
        setattr(other_team_info, column, getattr(TEAM_INFO, column))
        with pytest.raises(DuplicatedTeamError, match=column):
            await db_service.add_team(other_team_info)
        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1

    async def test_update_team_success(
        self, db_service: DBService, db_session: orm.Session, create_db_object: DBObjectCreator
    ) -> None:
        team_id = uuid4()
        base_db_team = make_db_team(**TEAM_INFO.dict(), team_id=team_id)
        create_db_object(base_db_team)
        updated_team = await db_service.update_team(team_id, OTHER_TEAM_INFO)
        for field in TeamInfo.schema()["properties"].keys():
            assert getattr(OTHER_TEAM_INFO, field) == getattr(updated_team, field)
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
        create_db_object(make_db_team(**TEAM_INFO.dict()))

        team_id = uuid4()
        base_db_team = make_db_team(**OTHER_TEAM_INFO.dict(), team_id=team_id)
        create_db_object(base_db_team)

        updated_team_info = OTHER_TEAM_INFO.copy()
        setattr(updated_team_info, column, getattr(TEAM_INFO, column))
        with pytest.raises(DuplicatedTeamError, match=column):
            await db_service.update_team(team_id, updated_team_info)

    async def test_update_nonexistent_team(self, db_service: DBService) -> None:
        with pytest.raises(TeamNotFoundError):
            await db_service.update_team(uuid4(), OTHER_TEAM_INFO)

    async def test_get_team_by_chat_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        db_team = make_db_team(**TEAM_INFO.dict())
        create_db_object(db_team)
        team = await db_service.get_team_by_chat(TEAM_INFO.chat_id)
        assert_db_model_equal_to_pydantic_model(db_team, team)

    async def test_get_nonexistent_team_by_chat_success(self, db_service: DBService) -> None:
        team = await db_service.get_team_by_chat(TEAM_INFO.chat_id)
        assert team is None


class TestModels:
    async def test_add_model_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_info = gen_model_info(team_id)

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
        team_id = add_team(TEAM_INFO, create_db_object)
        model_info = gen_model_info(team_id)
        add_model(model_info, create_db_object)

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
        model_info = gen_model_info(uuid4())
        with pytest.raises(TeamNotFoundError):
            await db_service.add_model(model_info)

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 0

    async def test_get_team_models_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_1_info = gen_model_info(team_id, rnd="1")
        add_model(model_1_info, create_db_object)
        model_2_info = gen_model_info(team_id, rnd="2")
        add_model(model_2_info, create_db_object)

        models = await db_service.get_team_models(team_id)
        assert sorted(m.name for m in models) == [model_1_info.name, model_2_info.name]

    async def test_get_team_models_when_no_models(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)

        models = await db_service.get_team_models(team_id)
        assert len(models) == 0
