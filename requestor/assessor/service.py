import typing as tp

import pandas as pd
from asgiref.sync import sync_to_async
from pydantic import BaseModel
from rectools import Columns
from rectools.metrics import calc_metrics

from requestor.gunner import UserRecoResponse
from requestor.models import Metric
from requestor.settings import config


class AssessorService(BaseModel):
    interactions: pd.DataFrame

    class Config:
        arbitrary_types_allowed = True

    async def prepare_recos(self, recos: tp.List[UserRecoResponse]) -> pd.DataFrame:
        return await sync_to_async(self._prepare_recos)(recos)

    def _prepare_recos(self, recos: tp.List[UserRecoResponse]) -> pd.DataFrame:
        user_reco = []
        for reco in recos:
            user_reco.extend(reco.prepare())

        return pd.DataFrame(
            user_reco,
            columns=[
                Columns.User,
                Columns.Item,
                Columns.Rank,
            ],
        )

    async def estimate_recos(self, recos: pd.DataFrame) -> tp.List[Metric]:
        return await sync_to_async(self._estimate_recos)(recos)

    def _estimate_recos(self, recos: pd.DataFrame) -> tp.List[Metric]:
        quality: tp.Dict[str, float] = calc_metrics(
            metrics=config.assessor_config.metrics,
            reco=recos,
            interactions=self.interactions,
        )
        metric_data = []
        for metric_name, metric_value in quality.items():
            metric_data.append(Metric(name=metric_name, value=metric_value))

        return metric_data
