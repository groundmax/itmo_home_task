import typing as tp
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4

import gspread
from pydantic import BaseModel
from pytest_httpserver import HTTPServer

from requestor.db.models import (
    Base,
    MetricsTable,
    ModelsTable,
    TeamsTable,
    TokensTable,
    TrialsTable,
)
from requestor.gunner import UserRecoResponse
from requestor.models import ModelInfo, TeamInfo, TokenInfo, TrialStatus

DBObjectCreator = tp.Callable[[Base], None]

MAX_WORKSHEET_ROWS = 1000
MAX_WORKSHEET_COL = "Y"

TOKEN_INFO = TokenInfo(
    token="super_token",
    team_description="super_description",
)

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


def make_db_token(
    token: str = "some_token",
    team_description: str = "desc",
) -> TokensTable:
    return TokensTable(
        token=token,
        team_description=team_description,
    )


def make_db_team(
    team_id: tp.Optional[UUID] = None,
    description: tp.Optional[str] = None,
    title: str = "some_title",
    chat_id: int = 12345,
    api_base_url: str = "some_url",
    api_key: tp.Optional[str] = "some_key",
    created_at: datetime = datetime(2022, 10, 11),
    updated_at: datetime = datetime(2022, 10, 11),
) -> TeamsTable:
    return TeamsTable(
        team_id=str(team_id or uuid4()),
        description="some_description_" + str(uuid4()) if description is None else description,
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


def make_db_trial(
    trial_id: tp.Optional[UUID] = None,
    model_id: tp.Optional[UUID] = None,
    created_at: datetime = datetime(2022, 10, 11),
    finished_at: datetime = datetime(2022, 10, 12),
    status: TrialStatus = TrialStatus.started,
) -> TeamsTable:
    return TrialsTable(
        trial_id=str(trial_id or uuid4()),
        model_id=str(model_id or uuid4()),
        created_at=created_at,
        finished_at=finished_at,
        status=status,
    )


def add_token(
    token_info: TokenInfo,
    create_db_object: DBObjectCreator,
) -> None:
    create_db_object(make_db_token(**token_info.dict()))


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
    create_db_object(
        make_db_model(**model_info.dict(), model_id=model_id, created_at=datetime.now())
    )
    return model_id


def add_trial(
    model_id: UUID,
    status: TrialStatus,
    create_db_object: DBObjectCreator,
    created_at: datetime = datetime(2022, 10, 11),
) -> UUID:
    trial_id = uuid4()
    create_db_object(
        make_db_trial(trial_id=trial_id, model_id=model_id, status=status, created_at=created_at)
    )
    return trial_id


def add_metric(
    trial_id: UUID,
    name: str,
    value: float,
    create_db_object: DBObjectCreator,
) -> None:
    metric = MetricsTable(
        trial_id=str(trial_id),
        name=name,
        value=value,
    )
    create_db_object(metric)


def gen_model_info(team_id: UUID, rnd: str = "") -> ModelInfo:
    return ModelInfo(team_id=team_id, name=f"some_name_{rnd}", description=f"some_desc_{rnd}")


def gen_team_info(rnd: int = 0) -> TeamInfo:
    return TeamInfo(
        title=f"title_{rnd}",
        chat_id=12345 + rnd,
        api_base_url=f"url_{rnd}",
        api_key=f"key_{rnd}",
    )


def clear_spreadsheet(ss: gspread.Spreadsheet) -> None:
    for ws in ss.worksheets():
        ws.batch_clear([f"A2:{MAX_WORKSHEET_COL}{MAX_WORKSHEET_ROWS}"])


def gen_json_reco_response(
    user_id: int, items_size: int
) -> tp.Dict[str, tp.Union[int, tp.List[int]]]:
    return {"user_id": user_id, "items": list(range(items_size))}


def gen_model_user_reco_response(user_id: int, items_size: int) -> UserRecoResponse:
    return UserRecoResponse(**gen_json_reco_response(user_id, items_size))


class ResponseTypes(Enum):
    ok = "ok"
    contains_null = "contains_null"
    contains_duplicates = "contains_duplicates"
    incorrect_reco_size = "incorrect_reco_size"
    incorrect_model_response = "incorrect_model_response"
    huge_bytes_size = "huge_bytes_size"


def gen_response_based_on_type(
    user_id: int,
    reco_size: int,
    response_type: ResponseTypes,
) -> tp.Dict[str, tp.Union[int, tp.List[tp.Optional[int]]]]:
    if response_type == ResponseTypes.ok:
        response = gen_json_reco_response(user_id, reco_size)
    elif response_type == ResponseTypes.contains_null:
        response = {"user_id": user_id, "items": list(range(reco_size - 1)) + [None]}
    elif response_type == ResponseTypes.contains_duplicates:
        response = {"user_id": user_id, "items": [0 for _ in range(reco_size)]}
    elif response_type == ResponseTypes.incorrect_reco_size:
        response = {"user_id": user_id, "items": list(range(reco_size - 1))}
    elif response_type == ResponseTypes.incorrect_model_response:
        response = {"items": list(range(reco_size))}
    elif response_type == ResponseTypes.huge_bytes_size:
        response = gen_json_reco_response(user_id, 10**6)
    else:
        raise ValueError("There is no such response type")

    return response


def prepare_http_responses(
    httpserver: HTTPServer,
    users_batches: tp.List[tp.List[int]],
    reco_size: int,
    response_type: ResponseTypes,
    user_id_with_custom_response: int = 2,
) -> None:
    httpserver.expect_request("/health").respond_with_data("DATA")
    for users_batch in users_batches:
        for user_id in users_batch:
            if user_id == user_id_with_custom_response:
                response = gen_response_based_on_type(user_id, reco_size, response_type)
            else:
                response = gen_json_reco_response(user_id, reco_size)
            httpserver.expect_request(f"/model_name/{user_id}").respond_with_json(response)
