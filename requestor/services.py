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


# TODO: load user_ids and interactions from S3/file/Yandex Disk
def make_gunner_service(config: ServiceConfig) -> GunnerService:
    df = pd.read_csv("./venv/interactions.csv", usecols=[Columns.User]).head(10**3)
    users = df[Columns.User].unique().tolist()
    users_batches = chunkify(users, config.gunner_config.user_request_batch_size)
    return GunnerService(users_batches=users_batches)


def make_assessor_service() -> AssessorService:
    interactions = pd.read_csv("./venv/interactions.csv").head(10**3)
    return AssessorService(interactions=interactions)


class App(BaseModel):
    assessor_service: AssessorService
    db_service: DBService
    gs_service: GSService
    gunner_service: GunnerService
