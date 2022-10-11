import typing as tp
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel

from requestor.db.models import Base, TeamsTable

DBObjectCreator = tp.Callable[[Base], None]


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


# T = tp.TypeVar("T", bound=Base)
#
#
# def make_db_model_from_pydantic_model(
#     db_model_type: tp.Type[T],
#     pydantic_model: BaseModel,
# ) -> T:
#     values = pydantic_model.dict()
#
#     for field in pydantic_model.schema()["properties"].keys():
#         db_val = getattr(db_model, field)
#         pydantic_val = getattr(pydantic_model, field)
#         if isinstance(pydantic_val, UUID):
#             pydantic_val = str(pydantic_val)
#         assert db_val == pydantic_val
#
