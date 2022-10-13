# pylint: disable=attribute-defined-outside-init
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import orm

from requestor.db.exceptions import (
    DuplicatedModelError,
    DuplicatedTeamError,
    ModelNotFoundError,
    TeamNotFoundError,
    TrialNotFoundError,
)
from requestor.db.models import ModelsTable, TeamsTable, TrialsTable
from requestor.db.service import DBService
from requestor.models import ModelInfo, TeamInfo, TrialStatus
from requestor.utils import utc_now
from tests.utils import (
    OTHER_TEAM_INFO,
    TEAM_INFO,
    ApproxDatetime,
    DBObjectCreator,
    add_model,
    add_team,
    add_trial,
    assert_db_model_equal_to_pydantic_model,
    gen_model_info,
    make_db_team,
    make_db_trial,
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

    async def test_add_model_with_same_name_for_other_team(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        other_team_id = add_team(OTHER_TEAM_INFO, create_db_object)
        model_info = gen_model_info(team_id)
        add_model(model_info, create_db_object)

        other_model_info = model_info.copy()
        other_model_info.team_id = other_team_id
        await db_service.add_model(other_model_info)

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 2

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


class TestTrials:
    @pytest.mark.parametrize("status", (TrialStatus.started, TrialStatus.waiting))
    async def test_add_trial_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        status: TrialStatus,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_id = add_model(gen_model_info(team_id), create_db_object)

        trial = await db_service.add_trial(model_id, status)
        assert trial.model_id == model_id
        assert trial.created_at == ApproxDatetime(utc_now())
        assert trial.finished_at is None
        assert trial.status == status

        db_trials = db_session.query(TrialsTable).all()
        assert len(db_trials) == 1
        assert_db_model_equal_to_pydantic_model(db_trials[0], trial)

    @pytest.mark.parametrize("status", (TrialStatus.success, TrialStatus.failed))
    async def test_add_finished_trial(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        status: TrialStatus,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_id = add_model(gen_model_info(team_id), create_db_object)

        with pytest.raises(ValueError):
            await db_service.add_trial(model_id, status)

        db_trials = db_session.query(TrialsTable).all()
        assert len(db_trials) == 0

    async def test_add_trial_for_nonexistent_model(
        self,
        db_service: DBService,
        db_session: orm.Session,
    ) -> None:
        with pytest.raises(ModelNotFoundError):
            await db_service.add_trial(uuid4(), TrialStatus.started)

        db_trials = db_session.query(TrialsTable).all()
        assert len(db_trials) == 0

    @pytest.mark.parametrize("status", TrialStatus)
    async def test_update_trial_status(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        status: TrialStatus,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_id = add_model(gen_model_info(team_id), create_db_object)
        trial_id = add_trial(model_id, TrialStatus.started, create_db_object)

        trial = await db_service.update_trial_status(trial_id, status)

        assert trial.finished_at == (ApproxDatetime(utc_now()) if status.is_finished() else None)
        assert trial.status == status

        db_trials = db_session.query(TrialsTable).all()
        assert len(db_trials) == 1
        assert_db_model_equal_to_pydantic_model(db_trials[0], trial)

    async def test_update_nonexistent_trial_status(self, db_service: DBService) -> None:
        with pytest.raises(TrialNotFoundError):
            await db_service.update_trial_status(uuid4(), TrialStatus.success)

    async def test_get_trial_today_stat(
        self,
        db_service: DBService,
        create_db_object: DBObjectCreator,
    ) -> None:
        t1_id = add_team(TEAM_INFO, create_db_object)
        t2_id = add_team(OTHER_TEAM_INFO, create_db_object)

        t1_m1_id = add_model(gen_model_info(t1_id), create_db_object)
        t1_m2_id = add_model(gen_model_info(t1_id, rnd="2"), create_db_object)
        t2_m1_id = add_model(gen_model_info(t2_id), create_db_object)

        today = utc_now()
        yesterday = utc_now() - timedelta(days=1)

        trials = (
            make_db_trial(model_id=t1_m1_id, status=TrialStatus.started, created_at=today),
            make_db_trial(model_id=t1_m1_id, status=TrialStatus.started, created_at=today),
            make_db_trial(model_id=t1_m1_id, status=TrialStatus.success, created_at=today),
            make_db_trial(model_id=t1_m1_id, status=TrialStatus.success, created_at=yesterday),
            make_db_trial(model_id=t1_m2_id, status=TrialStatus.waiting, created_at=today),
            make_db_trial(model_id=t1_m2_id, status=TrialStatus.failed, created_at=today),
            make_db_trial(model_id=t2_m1_id, status=TrialStatus.started, created_at=today),
        )
        for trial in trials:
            create_db_object(trial)

        t1_trials_stat = await db_service.get_team_today_trial_stat(t1_id)

        assert t1_trials_stat == {
            TrialStatus.started: 2,
            TrialStatus.waiting: 1,
            TrialStatus.success: 1,
            TrialStatus.failed: 1,
        }
