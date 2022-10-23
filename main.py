import asyncio

from requestor.bot import dp, config, register_handlers, bot, BotCommands
from requestor.services import make_db_service
from requestor.log import setup_logging

async def main():
    db_service = make_db_service(config)
    register_handlers(dp, db_service, config)
    setup_logging(config)

    await bot.set_my_commands(commands=BotCommands.get_bot_commands())
    await db_service.setup()
    try:
        await dp.start_polling()
    finally:
        await db_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
