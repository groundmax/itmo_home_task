import asyncio
from requestor.bot import dp, register_handlers, bot, BotCommands
from requestor.services import make_db_service, make_gs_service, make_assessor_service, make_gunner_service, App
from requestor.settings import config, StorageServiceConfig
from requestor.log import setup_logging
from requestor.utils import get_interactions_from_s3
import io
import pandas as pd



async def main():
    db_service = make_db_service(config)
    gs_service = make_gs_service(config)

    s3_storage_config = StorageServiceConfig()
    interactions = get_interactions_from_s3(s3_storage_config)

    print(interactions.shape)
    print(interactions.head())

    gunner_service = make_gunner_service(config, interactions)
    assessor_service = make_assessor_service(interactions)

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
