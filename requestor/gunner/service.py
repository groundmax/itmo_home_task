import asyncio
import typing as tp
from asyncio import Task
from http import HTTPStatus

from aiohttp import ClientSession
from pydantic import validator
from pydantic.main import BaseModel

from requestor.settings import config

from .exceptions import (
    AuthorizationError,
    DuplicatedRecommendationsError,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
)

START_RANK_FROM: tp.Final = 1

RecommendationRow = tp.Tuple[int, int, int]
UserResponseInfo = tp.Tuple[int, tp.Dict[str, tp.Any], int]


class UserRecoResponse(BaseModel):
    user_id: int
    items: tp.List[int]

    def prepare(self) -> tp.List[RecommendationRow]:
        return [
            (self.user_id, item_id, rank)
            for rank, item_id in enumerate(self.items, START_RANK_FROM)
        ]

    @validator("items")
    @classmethod
    def check_duplicates(cls, value: tp.List[int]) -> tp.List[int]:
        if len(set(value)) != len(value):
            raise DuplicatedRecommendationsError("Recommended items should be unique.")

        return value

    @validator("items")
    @classmethod
    def check_reco_size(cls, value: tp.List[int]) -> tp.List[int]:
        reco_size = config.assessor_config.reco_size
        if len(value) != reco_size:
            raise RecommendationsLimitSizeError(
                f"There should be exactly {reco_size} items in recommendations."
            )

        return value


class GunnerService(BaseModel):
    users_batches: tp.List[tp.List[int]]

    class Config:
        arbitrary_types_allowed = True

    async def request(
        self,
        session: ClientSession,
        request_url: str,
        user_id: int,
    ) -> UserResponseInfo:
        async with session.get(request_url) as response:
            resp_size = response.content.total_bytes
            if resp_size > config.gunner_config.max_resp_bytes_size:
                raise HugeResponseSizeError(f"Got too big response size for user `{user_id}`.")

            resp = await response.json()

            return user_id, resp, response.status

    async def ping(self, session: ClientSession, api_base_url: str) -> int:
        async with session.get(f"{api_base_url}/health") as response:
            return response.status

    def get_tasks(
        self,
        queue: tp.Dict[int, int],
        session: ClientSession,
        api_base_url: str,
        model_name: str,
    ) -> tp.List[Task]:
        tasks = []
        for user_id, n_times_requested in queue.items():
            if n_times_requested >= config.gunner_config.max_n_times_requested:
                raise RequestLimitByUserError(f"User_id `{user_id}` reached request limit")

            url = config.gunner_config.request_url_template.format(
                api_base_url=api_base_url,
                model_name=model_name,
                user_id=user_id,
            )

            tasks.append(asyncio.create_task(self.request(session, url, user_id)))
        return tasks

    def init_queue(self, users_batch: tp.List[int]) -> tp.Dict[int, int]:
        return {user_id: 0 for user_id in users_batch}

    async def get_recos(
        self,
        api_base_url: str,
        model_name: str,
        api_token: tp.Optional[str] = None,
    ) -> tp.List[UserRecoResponse]:
        results = []

        if api_token is not None:
            headers = {"Authorization": f"Bearer {api_token}"}
        else:
            headers = None

        async with ClientSession(headers=headers) as session:
            status = await self.ping(session, api_base_url)
            if status == HTTPStatus.UNAUTHORIZED:
                raise AuthorizationError(
                    "There is a problem with authorization, check your API token"
                )

            for users_batch in self.users_batches:
                queue = self.init_queue(users_batch)
                while queue:
                    tasks = self.get_tasks(queue, session, api_base_url, model_name)
                    responses: tp.List[UserResponseInfo] = await asyncio.gather(*tasks)

                    for user_id, response, status in responses:

                        if status != HTTPStatus.OK:
                            queue[user_id] += 1
                            continue

                        model_response = UserRecoResponse(**response)

                        del queue[user_id]
                        results.append(model_response)

        return results
