# pylint: disable=attribute-defined-outside-init
import typing as tp
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import orm

from requestor.db.exceptions import (
    DuplicatedMetricError,
    DuplicatedModelError,
    DuplicatedTeamError,
    ModelNotFoundError,
    TeamNotFoundError,
    TokenNotFoundError,
    TrialNotFoundError,
)
from requestor.db.models import MetricsTable, ModelsTable, TeamsTable, TokensTable, TrialsTable
from requestor.db.service import DBService
from requestor.models import (
    ByModelLeaderboardRow,
    GlobalLeaderboardRow,
    Metric,
    ModelInfo,
    TeamInfo,
    TrialStatus,
)
from requestor.utils import utc_now
from tests.utils import (
    OTHER_TEAM_INFO,
    TEAM_INFO,
    TOKEN_INFO,
    ApproxDatetime,
    DBObjectCreator,
    add_metric,
    add_model,
    add_team,
    add_token,
    add_trial,
    assert_db_model_equal_to_pydantic_model,
    gen_model_info,
    gen_team_info,
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
        create_db_object: DBObjectCreator,
    ) -> None:
        add_token(TOKEN_INFO, create_db_object)
        team = await db_service.add_team(TEAM_INFO, TOKEN_INFO.token)
        for field in TeamInfo.schema()["properties"].keys():
            assert getattr(TEAM_INFO, field) == getattr(team, field)
        assert team.created_at == ApproxDatetime(utc_now())
        assert team.updated_at == ApproxDatetime(utc_now())
        assert team.description == TOKEN_INFO.team_description

        db_teams = db_session.query(TeamsTable).all()
        assert len(db_teams) == 1
        db_team = db_teams[0]
        assert_db_model_equal_to_pydantic_model(db_team, team)

        assert db_session.query(TokensTable).count() == 0

    @pytest.mark.parametrize("column", ("title", "chat_id", "api_base_url"))
    async def test_add_duplicated_team(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
        column: str,
    ) -> None:
        create_db_object(make_db_team(**TEAM_INFO.dict()))

        add_token(TOKEN_INFO, create_db_object)
        other_team_info = OTHER_TEAM_INFO.copy()
        setattr(other_team_info, column, getattr(TEAM_INFO, column))
        with pytest.raises(DuplicatedTeamError, match=column):
            await db_service.add_team(other_team_info, TOKEN_INFO.token)
        assert db_session.query(TeamsTable).count() == 1

    async def test_add_team_with_duplicated_description(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        create_db_object(make_db_team(**TEAM_INFO.dict(), description=TOKEN_INFO.team_description))

        add_token(TOKEN_INFO, create_db_object)
        other_team_info = OTHER_TEAM_INFO.copy()

        with pytest.raises(DuplicatedTeamError, match="description"):
            await db_service.add_team(other_team_info, TOKEN_INFO.token)
        assert db_session.query(TeamsTable).count() == 1

    async def test_add_team_with_nonexistent_token(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        add_token(TOKEN_INFO, create_db_object)

        with pytest.raises(TokenNotFoundError):
            await db_service.add_team(TEAM_INFO, "other_token")
        assert db_session.query(TeamsTable).count() == 0
        assert db_session.query(TokensTable).count() == 1

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

    async def test_get_nonexistent_team_by_chat(self, db_service: DBService) -> None:
        with pytest.raises(TeamNotFoundError):
            await db_service.get_team_by_chat(TEAM_INFO.chat_id)


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

    async def test_get_team_last_n_models_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_1_info = gen_model_info(team_id, rnd="1")
        add_model(model_1_info, create_db_object)
        model_2_info = gen_model_info(team_id, rnd="2")
        add_model(model_2_info, create_db_object)
        model_3_info = gen_model_info(team_id, rnd="3")
        add_model(model_3_info, create_db_object)

        models = await db_service.get_team_last_n_models(team_id, 2)
        assert [m.name for m in models] == [model_3_info.name, model_2_info.name]

    async def test_get_team_last_n_models_when_no_models(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)

        models = await db_service.get_team_last_n_models(team_id, 1)
        assert len(models) == 0

    async def test_get_team_last_n_models_negative_limit(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        with pytest.raises(ValueError):
            await db_service.get_team_last_n_models(team_id, 0)

    async def test_get_model_by_name_success(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_1_info = gen_model_info(team_id, rnd="1")
        add_model(model_1_info, create_db_object)

        model_1 = await db_service.get_model_by_name(team_id, model_1_info.name)
        assert model_1.name == model_1_info.name

    async def test_get_model_by_name_exception(
        self, db_service: DBService, create_db_object: DBObjectCreator
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        with pytest.raises(ModelNotFoundError):
            await db_service.get_model_by_name(team_id, "non_existent_name")


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

        assert trial.finished_at == (ApproxDatetime(utc_now()) if status.is_finished else None)
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


class TestMetrics:
    async def test_add_metrics_success(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_id = add_model(gen_model_info(team_id), create_db_object)
        trial_id = add_trial(model_id, TrialStatus.started, create_db_object)
        metrics = [Metric(name="m1", value=10), Metric(name="m2", value=20)]

        await db_service.add_metrics(trial_id, metrics)

        db_metrics = db_session.query(MetricsTable).all()
        assert len(db_metrics) == 2

    async def test_add_duplicated_metrics(
        self,
        db_service: DBService,
        db_session: orm.Session,
        create_db_object: DBObjectCreator,
    ) -> None:
        team_id = add_team(TEAM_INFO, create_db_object)
        model_id = add_model(gen_model_info(team_id), create_db_object)
        trial_id = add_trial(model_id, TrialStatus.started, create_db_object)
        metrics = [Metric(name="m1", value=10), Metric(name="m1", value=20)]

        with pytest.raises(DuplicatedMetricError, match="trial_id, name"):
            await db_service.add_metrics(trial_id, metrics)

        db_metrics = db_session.query(MetricsTable).all()
        assert len(db_metrics) == 0

    async def test_add_metrics_for_nonexistent_trial(
        self,
        db_service: DBService,
        db_session: orm.Session,
    ) -> None:
        metrics = [Metric(name="m1", value=10), Metric(name="m1", value=20)]

        with pytest.raises(TrialNotFoundError):
            await db_service.add_metrics(uuid4(), metrics)

        db_metrics = db_session.query(MetricsTable).all()
        assert len(db_metrics) == 0


class TestLeaderboard:
    def setup(self) -> None:
        self.now = utc_now()
        self.now_1 = self.now - timedelta(hours=1)
        self.now_2 = self.now - timedelta(hours=2)
        self.now_3 = self.now - timedelta(hours=3)

    @tp.no_type_check
    def _add_data(self, create_db_object: DBObjectCreator) -> tp.Dict:  # pylint: disable=too-many-locals
        # 1 - team with 2 models, both have trials
        # 2 - team with 2 models, only 1st has trials
        # 3 - team with model with successful trial, but without metrics
        # 4 - team with model, but without successful trials
        # 5 - team with model, but without trials
        # 6 - team without models

        data = {}

        # Add teams
        for i in range(1, 7):
            t_info = gen_team_info(i)
            t_desc = f"desc_{t_info.title}"
            t_id = add_team(t_info, create_db_object, description=t_desc)
            data[i] = {"id": t_id, "description": t_desc}

        # Add models
        for i in (1, 2):
            data[i]["models"] = {}
            for j in (1, 2):
                t_id = data[i]["id"]
                m_info = gen_model_info(t_id, rnd=j)
                m_id = add_model(m_info, create_db_object)
                data[i]["models"][j] = {"id": m_id, "name": m_info.name}
        for i in (3, 4, 5):
            t_id = data[i]["id"]
            m_info = gen_model_info(t_id, rnd=1)
            m_id = add_model(m_info, create_db_object)
            data[i]["models"] = {1: {"id": m_id, "name": m_info.name}}

        # Add trials
        for i in (1, 2, 3, 4):
            models = data[i]["models"]
            for j, m in models.items():
                m_id = m["id"]
                statuses = (TrialStatus.waiting, TrialStatus.started, TrialStatus.failed)
                status = statuses[(i + j) % 3]
                tr_id = add_trial(m_id, status, create_db_object, created_at=self.now)
                m["trials"] = {1: {"id": tr_id, "dt": self.now}}

        model = data[1]["models"][1]
        tr_1_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now_1)
        tr_2_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now_3)
        model["trials"][2] = {"id": tr_1_id, "dt": self.now_1}
        model["trials"][3] = {"id": tr_2_id, "dt": self.now_3}

        model = data[1]["models"][2]
        tr_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now_2)
        model["trials"][2] = {"id": tr_id, "dt": self.now_2}

        model = data[2]["models"][1]
        tr_1_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now)
        tr_2_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now_2)
        model["trials"][2] = {"id": tr_1_id, "dt": self.now}
        model["trials"][3] = {"id": tr_2_id, "dt": self.now_2}

        model = data[3]["models"][1]
        tr_id = add_trial(model["id"], TrialStatus.success, create_db_object, self.now_2)
        model["trials"][2] = {"id": tr_id, "dt": self.now_2}

        # Add metrics
        tr_id = data[1]["models"][1]["trials"][2]["id"]
        add_metric(tr_id, "metric_1", 10, create_db_object)
        add_metric(tr_id, "metric_2", 100, create_db_object)
        tr_id = data[1]["models"][1]["trials"][3]["id"]
        add_metric(tr_id, "metric_1", 20, create_db_object)

        tr_id = data[1]["models"][2]["trials"][2]["id"]
        add_metric(tr_id, "metric_1", 30, create_db_object)

        tr_id = data[2]["models"][1]["trials"][3]["id"]
        add_metric(tr_id, "metric_1", 50, create_db_object)

        return data

    async def test_global_leaderboard(
        self,
        db_service: DBService,
        create_db_object: DBObjectCreator,
    ) -> None:
        data = self._add_data(create_db_object)

        actual = await db_service.get_global_leaderboard("metric_1")

        expected = [
            GlobalLeaderboardRow(
                team_name=data[2]["description"],
                best_score=50,
                n_attempts=2,
                last_attempt=self.now,
            ),
            GlobalLeaderboardRow(
                team_name=data[1]["description"],
                best_score=30,
                n_attempts=3,
                last_attempt=self.now_1,
            ),
            GlobalLeaderboardRow(
                team_name=data[3]["description"],
                best_score=None,
                n_attempts=1,
                last_attempt=self.now_2,
            ),
            GlobalLeaderboardRow(
                team_name=data[4]["description"],
                best_score=None,
                n_attempts=0,
                last_attempt=None,
            ),
            GlobalLeaderboardRow(
                team_name=data[5]["description"],
                best_score=None,
                n_attempts=0,
                last_attempt=None,
            ),
            GlobalLeaderboardRow(
                team_name=data[6]["description"],
                best_score=None,
                n_attempts=0,
                last_attempt=None,
            ),
        ]

        assert actual[: len(expected)] == expected

    async def test_by_model_leaderboard(
        self,
        db_service: DBService,
        create_db_object: DBObjectCreator,
    ) -> None:
        data = self._add_data(create_db_object)

        actual = await db_service.get_by_model_leaderboard("metric_1")

        expected = [
            ByModelLeaderboardRow(
                team_name=data[1]["description"],
                model_name=data[1]["models"][1]["name"],
                best_score=20,
                n_attempts=2,
                last_attempt=self.now_1,
            ),
            ByModelLeaderboardRow(
                team_name=data[1]["description"],
                model_name=data[1]["models"][2]["name"],
                best_score=30,
                n_attempts=1,
                last_attempt=self.now_2,
            ),
            ByModelLeaderboardRow(
                team_name=data[2]["description"],
                model_name=data[2]["models"][1]["name"],
                best_score=50,
                n_attempts=1,
                last_attempt=self.now_2,
            ),
        ]

        assert actual == expected
