import asyncio

from aiogram.utils.executor import start_webhook

from requestor.bot import dp, register_handlers, bot, BotCommands
from requestor.services import make_db_service, make_gs_service, make_assessor_service, make_gunner_service, App
from requestor.settings import config, StorageServiceConfig
from requestor.log import setup_logging
from requestor.utils import get_interactions_from_s3
import io
import pandas as pd



async def main():
    setup_logging(config)
    app = App.from_config(config)

    register_handlers(dp, app, config)

    await bot.set_my_commands(commands=BotCommands.get_bot_commands())

    webhook_path_pattern = config.telegram_config.webhook_path_pattern
    webhook_path = webhook_path_pattern.format(bot_token=config.telegram_config.bot_token)
    webhook_url = config.telegram_config.webhook_host + webhook_path

    start_webhook(
        dispatcher=dp,
        webhook_path=webhook_path,
        skip_updates=True,
        on_startup=make_on_startup_handler(bot, app, webhook_url),
        on_shutdown=make_on_shutdown_handler(bot, app),
        host=config.telegram_config.host,
        port=config.telegram_config.port,
    )


if __name__ == "__main__":
    asyncio.run(main())
