from aiogram import Bot
from aiogram.dispatcher import Dispatcher

from requestor.settings import config

bot = Bot(token=config.telegram_config.bot_token)

dp = Dispatcher(bot)
