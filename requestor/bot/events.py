import typing as tp

from aiogram import Bot, Dispatcher

from requestor.services import App

from .commands import BotCommands

EventHandler = tp.Callable[[Dispatcher], tp.Coroutine[tp.Any, tp.Any, tp.Any]]


def make_on_startup_handler(bot: Bot, app: App, webhook_url: str) -> EventHandler:
    async def on_startup(dispatcher: Dispatcher) -> None:
        await app.setup()
        await bot.set_my_commands(commands=BotCommands.get_bot_commands())
        await bot.set_webhook(webhook_url, drop_pending_updates=False)

    return on_startup


def make_on_shutdown_handler(bot: Bot, app: App) -> EventHandler:
    async def on_shutdown(dispatcher: Dispatcher) -> None:
        await bot.delete_webhook()
        await app.cleanup()

    return on_shutdown
