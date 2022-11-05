import pandas as pd
import pytest
from rectools import Columns

from requestor.assessor import AssessorService
from requestor.models import Metric
from requestor.settings import ServiceConfig
from tests.utils import gen_model_user_reco_response

pytestmark = pytest.mark.asyncio


async def test_prepare_recos(
    assessor_service: AssessorService,
    service_config: ServiceConfig,
) -> None:
    user_reco_responses = [
        gen_model_user_reco_response(
            user_id=1,
            items_size=service_config.assessor_config.reco_size,
        )
    ]
    actual = await assessor_service.prepare_recos(user_reco_responses)

    data = [
        [1, 0, 1],
        [1, 1, 2],
        [1, 2, 3],
        [1, 3, 4],
        [1, 4, 5],
        [1, 5, 6],
        [1, 6, 7],
        [1, 7, 8],
        [1, 8, 9],
        [1, 9, 10],
    ]

    expected = pd.DataFrame(
        data=data,
        columns=[
            Columns.User,
            Columns.Item,
            Columns.Rank,
        ],
    )

    assert (actual == expected).all().all()


async def test_estimate_recos(
    assessor_service: AssessorService,
    service_config: ServiceConfig,
) -> None:
    assessor_config = service_config.assessor_config

    user_reco_responses = [
        gen_model_user_reco_response(
            user_id=1,
            items_size=assessor_config.reco_size,
        )
    ]
    recos = await assessor_service.prepare_recos(user_reco_responses)
    actual = await assessor_service.estimate_recos(recos)
    expected = [Metric(name=assessor_config.main_metric_name, value=0.5)]

    assert actual == expected
