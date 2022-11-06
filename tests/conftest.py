# pylint: disable=redefined-outer-name
import os
import typing as tp
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import gspread
import pytest
import sqlalchemy as sa
from alembic import command as alembic_command
from alembic import config as alembic_config
from sqlalchemy import orm

from requestor.db.models import Base
from requestor.db.service import DBService
from requestor.google import GSService
from requestor.services import make_db_service, make_gs_service
from requestor.settings import ServiceConfig, get_config
from tests.utils import DBObjectCreator, clear_spreadsheet

CURRENT_DIR = Path(__file__).parent
ALEMBIC_INI_PATH = CURRENT_DIR.parent / "alembic.ini"


@contextmanager
def sqlalchemy_bind_context(url: str) -> tp.Iterator[sa.engine.Engine]:
    bind = sa.engine.create_engine(url)
    try:
        yield bind
    finally:
        bind.dispose()


@contextmanager
def sqlalchemy_session_context(
    bind: sa.engine.Engine,
) -> tp.Iterator[orm.Session]:
    session_factory = orm.sessionmaker(bind)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def migrations_context(alembic_ini: Path) -> tp.Iterator[None]:
    cfg = alembic_config.Config(str(alembic_ini))

    alembic_command.upgrade(cfg, "head")
    try:
        yield
    finally:
        alembic_command.downgrade(cfg, "base")


@pytest.fixture(scope="session")
def db_url() -> str:
    return os.getenv("DB_URL")


@pytest.fixture(scope="session")
def db_bind(db_url: str) -> tp.Iterator[sa.engine.Engine]:
    with sqlalchemy_bind_context(db_url) as bind:
        yield bind


@pytest.fixture
def db_session(db_bind: sa.engine.Engine) -> tp.Iterator[orm.Session]:
    with migrations_context(ALEMBIC_INI_PATH):
        with sqlalchemy_session_context(db_bind) as session:
            yield session


@pytest.mark.asyncio
@pytest.fixture
async def db_service(
    db_session: orm.Session, service_config: ServiceConfig
) -> tp.AsyncGenerator[DBService, None]:
    service = make_db_service(service_config)
    await service.setup()
    try:
        yield service
    finally:
        await service.cleanup()


@pytest.fixture
def service_config() -> ServiceConfig:
    return get_config()


@pytest.fixture
def create_db_object(
    db_session: orm.Session,
) -> DBObjectCreator:
    assert db_session.is_active

    def create(obj: Base) -> None:
        db_session.add(obj)
        db_session.commit()

    return create


@pytest.fixture
def spreadsheet(service_config: ServiceConfig) -> tp.Iterator[gspread.Spreadsheet]:
    config = service_config.gs_config
    with NamedTemporaryFile("w+") as f:
        f.write(config.credentials)
        f.seek(0)
        sa = gspread.service_account(f.name)
    sheet = sa.open_by_url(config.url)
    clear_spreadsheet(sheet)

    yield sheet

    clear_spreadsheet(sheet)


@pytest.mark.asyncio
@pytest.fixture
async def gs_service(service_config: ServiceConfig, spreadsheet: gspread.Spreadsheet) -> GSService:
    service = make_gs_service(service_config)
    await service.setup()
    return service
