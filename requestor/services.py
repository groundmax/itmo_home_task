import pandas as pd
from asyncpg import create_pool
from pydantic import BaseModel
from rectools import Columns

from .assessor import AssesorService
from .db.service import DBService
from .google import GSService
from .gunner import GunnerService
from .settings import ServiceConfig


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
def make_gunner_service() -> GunnerService:
    df = pd.read_csv("./venv/interactions.csv", usecols=[Columns.User])
    return GunnerService(user_ids=df[Columns.User].unique().tolist())


def make_assessor_service() -> AssesorService:
    interactions = pd.read_csv("./venv/interactions.csv")
    return AssesorService(interactions=interactions)


class App(BaseModel):
    assessor_service: AssesorService
    db_service: DBService
    gs_service: GSService
    gunner_service: GunnerService
