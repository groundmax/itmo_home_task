from aiogram import Bot, Dispatcher
import typing as tp

from requestor.services import App

EventHandler = tp.Callable[[Dispatcher], None]


def make_on_startup_handler(bot: Bot, app: App, webhook_url: str) -> EventHandler:
    async def on_startup(dispatcher: Dispatcher):
        await app.setup()
        await bot.set_webhook(webhook_url, drop_pending_updates=False)

    return on_startup


def make_on_shutdown_handler(bot: Bot, app: App) -> EventHandler:
    async def on_shutdown(dispatcher: Dispatcher):
        await bot.delete_webhook()
        await app.cleanup()

    return on_shutdown
