import typing as tp
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel

from requestor.db.models import Base, ModelsTable, TeamsTable
from requestor.models import ModelInfo, TeamInfo

DBObjectCreator = tp.Callable[[Base], None]

TEAM_INFO = TeamInfo(
    title="some_title",
    chat_id=12345,
    api_base_url="some_url",
    api_key="some_key",
)

OTHER_TEAM_INFO = TeamInfo(
    title="other_title",
    chat_id=54321,
    api_base_url="other_url",
    api_key=None,
)


class ApproxDatetime:
    def __init__(
        self,
        expected: datetime,
        abs_delta: timedelta = timedelta(seconds=10),
    ) -> None:
        self.min_ = expected - abs_delta
        self.max_ = expected + abs_delta

    def __eq__(self, actual: tp.Any) -> bool:
        if isinstance(actual, str):
            dt = datetime.fromisoformat(actual)
        elif isinstance(actual, datetime):
            dt = actual
        else:
            return False
        return self.min_ <= dt <= self.max_


def assert_db_model_equal_to_pydantic_model(
    db_model: Base,
    pydantic_model: BaseModel,
) -> None:
    for field in pydantic_model.schema()["properties"].keys():
        db_val = getattr(db_model, field)
        pydantic_val = getattr(pydantic_model, field)
        if isinstance(pydantic_val, UUID):
            pydantic_val = str(pydantic_val)
        assert db_val == pydantic_val


def make_db_team(
    team_id: tp.Optional[UUID] = None,
    title: str = "some_title",
    chat_id: int = 12345,
    api_base_url: str = "some_url",
    api_key: tp.Optional[str] = "some_key",
    created_at: datetime = datetime(2022, 10, 11),
    updated_at: datetime = datetime(2022, 10, 11),
) -> TeamsTable:
    return TeamsTable(
        team_id=str(team_id or uuid4()),
        title=title,
        chat_id=chat_id,
        api_base_url=api_base_url,
        api_key=api_key,
        created_at=created_at,
        updated_at=updated_at,
    )


def make_db_model(
    model_id: tp.Optional[UUID] = None,
    team_id: tp.Optional[UUID] = None,
    name: str = "some_title",
    description: tp.Optional[str] = "some_title",
    created_at: datetime = datetime(2022, 10, 11),
) -> TeamsTable:
    return ModelsTable(
        model_id=str(model_id or uuid4()),
        team_id=str(team_id or uuid4()),
        name=name,
        description=description,
        created_at=created_at,
    )


def add_team(
    team_info: TeamInfo,
    create_db_object: DBObjectCreator,
) -> UUID:
    team_id = uuid4()
    create_db_object(make_db_team(**team_info.dict(), team_id=team_id))
    return team_id


def add_model(
    model_info: ModelInfo,
    create_db_object: DBObjectCreator,
) -> UUID:
    model_id = uuid4()
    create_db_object(make_db_model(**model_info.dict(), model_id=model_id))
    return model_id


def gen_model_info(team_id: UUID, rnd: str = "") -> ModelInfo:
    return ModelInfo(team_id=team_id, name=f"some_name_{rnd}", description=f"some_desc_{rnd}")
