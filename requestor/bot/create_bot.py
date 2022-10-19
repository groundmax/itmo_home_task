from aiogram import Bot
from aiogram.dispatcher import Dispatcher

from requestor.settings import get_config

config = get_config()

bot = Bot(token=config.telegram_config.bot_token)

dp = Dispatcher(bot)
