import asyncio
import typing as tp
from asyncio import Task

import aiohttp
import pandas as pd
from pydantic.main import BaseModel
from rectools import Columns
from rectools.metrics import calc_metrics

from .metrics import METRICS

UserRecoResponse = tp.Dict[int, tp.List[int]]
START_RANK_FROM: tp.Final = 1


class GunnerService(BaseModel):
    user_ids: tp.List[int]
    interactions: pd.DataFrame

    class Config:
        arbitrary_types_allowed = True

    # TODO: limit number of calls
    def get_tasks(
        self,
        session: aiohttp.ClientSession,
        api_base_url: str,
        model_name: str,
    ) -> tp.List[Task]:
        tasks = []
        for user_id in self.user_ids:
            tasks.append(
                asyncio.create_task(session.get(f"{api_base_url}/{model_name}/{user_id}"))
            )

        return tasks

    # TODO: limit number of calls, handle errors, add token if present
    async def get_recos(self, api_base_url: str, model_name: str) -> tp.List[UserRecoResponse]:
        results = []
        async with aiohttp.ClientSession as session:  # type: ignore[attr-defined]
            tasks = self.get_tasks(session, api_base_url, model_name)
            responses = await asyncio.gather(*tasks)

            for response in responses:
                results.append(await response.json())

        return results

    # TODO: validate length/duplicates/NaNs in response
    def prepare_recos(self, recos: tp.List[UserRecoResponse]) -> pd.DataFrame:
        user_reco = []
        for reco in recos:
            for user_id, item_ids in reco.items():
                for rank, item_id in enumerate(item_ids, START_RANK_FROM):
                    user_reco.append((user_id, item_id, rank))

        return pd.DataFrame(
            user_reco,
            columns=[
                Columns.User,
                Columns.Item,
                Columns.Rank,
            ],
        )

    def estimate_recos(self, recos: pd.DataFrame) -> tp.Dict[str, float]:
        return calc_metrics(
            metrics=METRICS,
            reco=recos,
            interactions=self.interactions,
        )
