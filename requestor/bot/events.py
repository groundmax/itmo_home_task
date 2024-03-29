import typing as tp

from aiogram import Bot, Dispatcher

from requestor.services import App, make_db_service

from ..log import app_logger
from ..settings import ServiceConfig
from .bot_utils import update_leaderboards
from .commands import BotCommands

EventHandler = tp.Callable[[Dispatcher], tp.Coroutine[tp.Any, tp.Any, tp.Any]]


def make_on_startup_handler(
    bot: Bot, app: App, webhook_url: tp.Optional[str], config: ServiceConfig
) -> EventHandler:
    async def on_startup(dispatcher: Dispatcher) -> None:
        app_logger.info("On startup handler started")
        # Do initialization again because of asyncio/asyncpg error
        # https://github.com/sqlalchemy/sqlalchemy/issues/6409
        app.db_service = make_db_service(config)

        await app.setup()
        await bot.set_my_commands(commands=BotCommands.get_bot_commands())
        if webhook_url is not None:
            await bot.set_webhook(webhook_url, drop_pending_updates=False)

        await update_leaderboards(
            app.db_service, app.gs_service, config.assessor_config.main_metric_name
        )
        app_logger.info("On startup handler finished")

    return on_startup


def make_on_shutdown_handler(bot: Bot, app: App) -> EventHandler:
    async def on_shutdown(dispatcher: Dispatcher) -> None:
        await bot.delete_webhook()
        await app.cleanup()

    return on_shutdown
