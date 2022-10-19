import asyncio

from asyncpg import create_pool

from requestor.db import DBService
from requestor.settings import get_config

from .create_bot import dp
from .handlers import register_handlers


async def main():
    config = get_config()
    db_config = config.db_config.dict()
    pool_config = db_config.pop("db_pool_config")
    pool_config["dsn"] = pool_config.pop("db_url")
    pool = create_pool(**pool_config)
    db_service = DBService(pool=pool)
    try:
        register_handlers(dp, db_service, config)
        await db_service.setup()
        await dp.start_polling()
    finally:
        await db_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())  # type: ignore
