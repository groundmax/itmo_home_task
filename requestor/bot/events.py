from aiogram import Bot, Dispatcher
import typing as tp


EventHandler = tp.Callable[[Dispatcher], None]


def make_on_startup_handler(bot: Bot, webhook_url: str) -> EventHandler:
    async def on_startup(dispatcher: Dispatcher):
        await bot.set_webhook(webhook_url, drop_pending_updates=False)

    return on_startup


def make_on_shutdown_handler(bot: Bot) -> EventHandler:
    async def on_shutdown(dispatcher: Dispatcher):
        await bot.delete_webhook()

    return on_shutdown
