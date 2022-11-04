import asyncio

from aiogram.utils.executor import start_webhook

from requestor.bot import create_bot
from requestor.bot.events import make_on_startup_handler, make_on_shutdown_handler
from requestor.services import App
from requestor.settings import config
from requestor.log import setup_logging


async def main():
    setup_logging(config)
    app = App.from_config(config)

    bot, dp = create_bot(app)

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
