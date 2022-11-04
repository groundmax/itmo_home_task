import asyncio
import sys
import typing as tp
from asyncio import Task
from http import HTTPStatus

from aiohttp import ClientResponse, ClientSession
from aiohttp.client import _RequestContextManager
from asgiref.sync import sync_to_async
from pydantic import validator
from pydantic.main import BaseModel

from requestor.settings import config

from .exceptions import (
    DuplicatedRecommendationsError,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
)

START_RANK_FROM: tp.Final = 1

RecommendationRow = tp.Tuple[int, int, int]
UserRequest = tp.Tuple[int, _RequestContextManager]


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

    def request(self, session: ClientSession, request_url: str, user_id: int) -> UserRequest:
        return user_id, session.get(request_url)

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
            async_request = sync_to_async(self.request)(session, url, user_id)
            tasks.append(asyncio.create_task(async_request))
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
            for users_batch in self.users_batches:
                queue = self.init_queue(users_batch)
                while queue:
                    tasks = self.get_tasks(queue, session, api_base_url, model_name)
                    responses: tp.List[UserRequest] = await asyncio.gather(*tasks)

                    for user_id, response_ in responses:
                        response: ClientResponse = await response_

                        if response.status != HTTPStatus.OK:
                            queue[user_id] += 1
                            continue

                        resp = await response.json()

                        model_response = UserRecoResponse(**resp)

                        resp_size = sys.getsizeof(resp)
                        if resp_size > config.gunner_config.max_resp_bytes_size:
                            raise HugeResponseSizeError(
                                f"Got too big response size for user `{user_id}`."
                            )

                        del queue[user_id]
                        results.append(model_response)

        return results
