import pandas as pd
from asyncpg import create_pool
from pydantic import BaseModel
from rectools import Columns

from .assessor import AssessorService
from .db.service import DBService
from .google import GSService
from .gunner import GunnerService
from .settings import ServiceConfig
from .utils import chunkify


def make_db_service(config: ServiceConfig) -> DBService:
    db_config = config.db_config.dict()
    pool_config = db_config.pop("db_pool_config")
    pool_config["dsn"] = pool_config.pop("db_url")
    pool = create_pool(**pool_config)
    service = DBService(pool=pool, **db_config)
    return service


def make_gs_service(config: ServiceConfig) -> GSService:
    return GSService(**config.gs_config.dict())


def make_gunner_service(config: ServiceConfig, interactions: pd.DataFrame) -> GunnerService:
    users = interactions[Columns.User].unique().tolist()
    users_batches = chunkify(users, config.gunner_config.user_request_batch_size)
    return GunnerService(users_batches=users_batches)


def make_assessor_service(interactions: pd.DataFrame) -> AssessorService:
    return AssessorService(interactions=interactions)


class App(BaseModel):
    assessor_service: AssessorService
    db_service: DBService
    gs_service: GSService
    gunner_service: GunnerService

    @classmethod
    def from_config(cls, config: ServiceConfig) -> "App":
        db_service = make_db_service(config)
        gs_service = make_gs_service(config)

        gunner_service = make_gunner_service(config)
        assessor_service = make_assessor_service()

        return App(
            assessor_service=assessor_service,
            db_service=db_service,
            gs_service=gs_service,
            gunner_service=gunner_service
        )

    async def setup(self) -> None:
        await self.db_service.setup()
        await self.gs_service.setup()

    async def cleanup(self) -> None:
        await self.db_service.cleanup()
