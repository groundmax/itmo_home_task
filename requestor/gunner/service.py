import asyncio
import typing as tp
from asyncio import Task
from http import HTTPStatus
from urllib.parse import urlsplit

from aiohttp import ClientSession, ClientTimeout
from pydantic import validator
from pydantic.main import BaseModel

from requestor.models import ProgressNotifier
from requestor.settings import config

from .exceptions import (
    DuplicatedRecommendationsError,
    HTTPAuthorizationError,
    HTTPResponseNotOKError,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
    RequestTimeoutError,
)

START_RANK_FROM: tp.Final = 1
NOT_REQUESTED_STATUS: tp.Final = -999
UPDATE_PERIOD: tp.Final = config.gunner_config.progress_update_period
TIMEOUT: tp.Final = ClientTimeout(total=config.gunner_config.timeout)

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
        scheme, netloc, _, _, _ = urlsplit(api_base_url)

        async with session.get(f"{scheme}://{netloc}/health") as response:
            return response.status

    async def get_tasks(
        self,
        queue: tp.Dict[int, tp.Tuple[int, int]],
        session: ClientSession,
        api_base_url: str,
        model_name: str,
    ) -> tp.List[Task]:
        tasks = []
        for user_id, (n_times_requested, last_status) in queue.items():
            if n_times_requested >= config.gunner_config.max_n_times_requested:
                raise RequestLimitByUserError(
                    f"User_id `{user_id}` reached request limit. HTTPError: {last_status}"
                )

            url = config.gunner_config.request_url_template.format(
                api_base_url=api_base_url,
                model_name=model_name,
                user_id=user_id,
            )

            tasks.append(asyncio.create_task(self.request(session, url, user_id)))
        return tasks

    def _init_queue(self, users_batch: tp.List[int]) -> tp.Dict[int, tp.Tuple[int, int]]:
        return {user_id: (0, NOT_REQUESTED_STATUS) for user_id in users_batch}

    def _validate_health_status(self, status) -> None:
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise HTTPAuthorizationError(
                "There is a problem with authorization, check your API token. "
                f"HTTPError: {status}"
            )
        if status != HTTPStatus.OK:
            raise HTTPResponseNotOKError(f"Healtchcheck failed. HTTPError: {status}")

    def _get_auth_headers(self, api_token: str) -> tp.Optional[tp.Dict[str, str]]:
        if api_token is not None:
            return {"Authorization": f"Bearer {api_token}"}

        return None

    async def _get_recos_by_users_batch(
        self,
        users_batch: tp.List[int],
        api_base_url: str,
        model_name: str,
        session: ClientSession,
        results: tp.List[UserRecoResponse],
    ):
        queue = self._init_queue(users_batch)
        while queue:
            tasks = await self.get_tasks(queue, session, api_base_url, model_name)
            responses: tp.List[UserResponseInfo] = await asyncio.gather(*tasks)

            for user_id, response, status in responses:

                if status != HTTPStatus.OK:
                    n_times_requested, _ = queue[user_id]
                    queue[user_id] = (n_times_requested + 1, status)
                    continue

                model_response = UserRecoResponse(**response)

                del queue[user_id]
                results.append(model_response)

    async def get_recos(
        self,
        api_base_url: str,
        model_name: str,
        notifier: tp.Optional[ProgressNotifier] = None,
        api_token: tp.Optional[str] = None,
    ) -> tp.List[UserRecoResponse]:
        results: tp.List[UserRecoResponse] = []

        headers = self._get_auth_headers(api_token)

        try:
            async with ClientSession(headers=headers, timeout=TIMEOUT) as session:
                health_status = await self.ping(session, api_base_url)

                self._validate_health_status(health_status)

                for batch_num, users_batch in enumerate(self.users_batches):
                    await self._get_recos_by_users_batch(
                        users_batch,
                        api_base_url,
                        model_name,
                        session,
                        results,
                    )

                    if notifier is not None and batch_num % UPDATE_PERIOD == 0:
                        progress = f"Progress: {batch_num/(len(self.users_batches)):.2%}"
                        await notifier.send_progress_update(progress)
        except asyncio.TimeoutError:
            raise RequestTimeoutError(
                "Request timeout, please, check if service responds fast enough"
            )

        return results
