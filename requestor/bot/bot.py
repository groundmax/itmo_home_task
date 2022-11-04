import typing as tp

from aiogram import Bot
from aiogram.dispatcher import Dispatcher

from requestor.services import App
from requestor.settings import config

from .handlers import register_handlers


def create_bot(app: App) -> tp.Union[Bot, Dispatcher]:
    bot = Bot(token=config.telegram_config.bot_token)
    dp = Dispatcher(bot)

    register_handlers(dp, app, config)

    return bot, dp
