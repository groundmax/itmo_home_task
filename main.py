import asyncio

from requestor.bot import dp, config, register_handlers
from requestor.services import make_db_service


async def main():
    db_service = make_db_service(config)
    register_handlers(dp, db_service, config)
    await db_service.setup()
    try:
        await dp.start_polling()
    finally:
        await db_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
