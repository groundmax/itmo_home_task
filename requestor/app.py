import asyncio

from aiogram import Bot, Dispatcher
from aiogram.utils.executor import start_webhook
from sqlalchemy.exc import OperationalError

from migrations.utils import upgrade_db
from requestor.bot import create_bot
from requestor.bot.events import make_on_shutdown_handler, make_on_startup_handler
from requestor.log import app_logger, setup_logging
from requestor.services import App
from requestor.settings import Env, config
from requestor.utils import do_with_retries


async def run_with_polling(bot: Bot, dp: Dispatcher, app: App) -> None:
    await make_on_startup_handler(bot, app, None, config)(dp)
    try:
        await dp.start_polling()
    finally:
        await make_on_shutdown_handler(bot, app)(dp)


def run_with_webhook(bot: Bot, dp: Dispatcher, app: App) -> None:
    webhook_path_pattern = config.telegram_config.webhook_path_pattern
    webhook_path = webhook_path_pattern.format(bot_token=config.telegram_config.bot_token)
    webhook_url = config.telegram_config.webhook_host + webhook_path

    start_webhook(
        dispatcher=dp,
        webhook_path=webhook_path,
        skip_updates=True,
        on_startup=make_on_startup_handler(bot, app, webhook_url, config),
        on_shutdown=make_on_shutdown_handler(bot, app),
        host=config.telegram_config.host,
        port=config.telegram_config.port,
    )


def run_app():
    setup_logging(config)

    if config.run_migrations:
        app_logger.info("Upgrading DB...")
        do_with_retries(upgrade_db, OperationalError, config.migration_attempts)

    app = App.from_config(config)
    bot, dp = create_bot(app)

    app_logger.info("Starting app...")
    if config.env == Env.PRODUCTION:
        run_with_webhook(bot, dp, app)
    else:
        asyncio.run(run_with_polling(bot, dp, app))
