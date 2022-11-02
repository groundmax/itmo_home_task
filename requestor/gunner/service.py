import asyncio
import sys
import typing as tp
from asyncio import Task
from http import HTTPStatus

import aiohttp
from pydantic import validator
from pydantic.main import BaseModel

from requestor.settings import (
    MAX_N_TIMES_REQUESTED,
    MAX_RESP_BYTES_SIZE,
    RECO_SIZE,
    REQUEST_URL_TEMPLATE,
)

from .exceptions import (
    DuplicatedRecommendationsError,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
)

START_RANK_FROM: tp.Final = 1

RecommendationRow = tp.Tuple[int, int, int]


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
        if len(value) != RECO_SIZE:
            raise RecommendationsLimitSizeError(
                f"There should be exactly {RECO_SIZE} items in recommendations."
            )

        return value


class GunnerService(BaseModel):
    user_ids: tp.List[int]

    class Config:
        arbitrary_types_allowed = True

    def get_tasks(
        self,
        queue: tp.Dict[int, int],
        session: aiohttp.ClientSession,
        api_base_url: str,
        model_name: str,
    ) -> tp.List[Task]:
        tasks = []
        for user_id, n_times_requested in queue.items():
            if n_times_requested >= MAX_N_TIMES_REQUESTED:
                raise RequestLimitByUserError(f"User_id `{user_id}` reached request limit")

            url = REQUEST_URL_TEMPLATE.format(
                api_base_url=api_base_url,
                model_name=model_name,
                user_id=user_id,
            )
            tasks.append(asyncio.create_task(session.get(url)))
        return tasks

    def init_queue(self) -> tp.Dict[int, int]:
        return {user_id: 0 for user_id in self.user_ids}

    async def get_recos(
        self,
        api_base_url: str,
        model_name: str,
        api_token: tp.Optional[str] = None,
    ) -> tp.List[UserRecoResponse]:
        results = []

        queue = self.init_queue()

        if api_token is not None:
            headers = {"Authorization": f"Bearer {api_token}"}
        else:
            headers = None

        async with aiohttp.ClientSession(headers=headers) as session:
            while queue:
                tasks = self.get_tasks(queue, session, api_base_url, model_name)
                responses: tp.List[aiohttp.ClientResponse] = await asyncio.gather(*tasks)

                for response in responses:

                    if response.status != HTTPStatus.OK:
                        _, user_id = response.url.path.rsplit("/", maxsplit=1)
                        queue[int(user_id)] += 1
                        continue

                    resp = await response.json()

                    model_response = UserRecoResponse(**resp)

                    resp_size = sys.getsizeof(resp)
                    if resp_size > MAX_RESP_BYTES_SIZE:
                        raise HugeResponseSizeError(
                            f"Got too big response size for user `{model_response.user_id}`."
                        )

                    del queue[model_response.user_id]
                    results.append(model_response)

        return results
