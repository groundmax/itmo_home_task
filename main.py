import asyncio
from requestor.bot import dp, register_handlers, bot, BotCommands
from requestor.services import make_db_service, make_gs_service, make_assessor_service, make_gunner_service, App
from requestor.settings import config
from requestor.log import setup_logging


async def main():
    db_service = make_db_service(config)
    gs_service = make_gs_service(config)

    gunner_service = make_gunner_service(config)
    assessor_service = make_assessor_service()

    app = App(
        assessor_service=assessor_service,
        db_service=db_service,
        gs_service=gs_service,
        gunner_service=gunner_service
    )

    register_handlers(dp, app, config)
    setup_logging(config)

    await bot.set_my_commands(commands=BotCommands.get_bot_commands())
    await db_service.setup()
    await gs_service.setup()
    try:
        await dp.start_polling()
    finally:
        await db_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
