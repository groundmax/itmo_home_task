import traceback
import typing as tp
from functools import partial

from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, text

from requestor.db import DBService, DuplicatedTeamError, TeamNotFoundError
from requestor.log import app_logger
from requestor.models import TeamInfo
from requestor.settings import ServiceConfig


def parse_msg_with_team_info(message: types.Message) -> tp.Optional[TeamInfo]:
    command = message.text.split(maxsplit=3)
    if len(command) == 4:
        _, title, api_base_url, api_key = command
    elif len(command) == 3:
        _, title, api_base_url = command
        api_key = None

    try:
        return TeamInfo(
            title=title, chat_id=message.chat.id, api_base_url=api_base_url, api_key=api_key
        )
    except NameError:
        return None


async def handle(handler, db_service: DBService, message: types.Message) -> None:
    try:
        await handler(message, db_service)
    except Exception:
        app_logger.error(traceback.format_exc())
        raise


async def start_h(message: types.Message, db_service: DBService) -> None:
    reply = text(
        "Привет! Я бот, который будет проверять сервисы",
        "в рамках курса по рекомендательным системам.",
        "Наберите /help для вывода списка доступных команд.",
    )
    await message.reply(reply)


async def help_h(event: types.Message, db_service: DBService) -> None:
    reply = text(
        bold("Список доступных команд:"),
        "/register_team team_name api_host api_key (опционально) - для регистрации команд",
        "/update_team team_name api_host api_key (опционально) - для обновления данных команды",
        "/show_current_team - для вывода данных по зарегистрированной команде",
        sep="\n",
    )
    await event.reply(reply, parse_mode=ParseMode.MARKDOWN)


async def register_team_h(message: types.Message, db_service: DBService) -> None:
    team_info = parse_msg_with_team_info(message)

    if team_info is None:
        reply = text(
            "Пожалуйста, введите данные в корректном формате.",
            "/register\_team team\_name api\_host api\_key (опционально)",
        )
        await message.reply(reply)
        return

    try:
        await db_service.add_team(team_info)
        reply = f"Команда `{team_info.title}` успешно зарегистрирована!"
    except DuplicatedTeamError as e:
        if e.column == "chat_id":
            reply = text(
                "Вы уже регистрировали команду. Если необходимо обновить что-то,",
                "пожалуйста, воспользуйтесь командой /update_team.",
            )
        elif e.column == "title":
            reply = text(
                f"Команда с именем `{team_info.title}` уже существует.",
                "Пожалуйста, выберите другое имя команды.",
            )
        elif e.column == "api_base_url":
            reply = text(
                f"Хост: `{team_info.api_base_url}` уже кем-то используется.",
                "Пожалуйста, выберите другой хост.",
            )
        else:
            reply = text(
                "Что-то пошло не так.",
                "Пожалуйста, попробуйте зарегистрироваться через несколько минут.",
            )

    await message.reply(reply)


async def update_team_h(message: types.Message, db_service: DBService) -> None:
    updated_team_info = parse_msg_with_team_info(message)

    if updated_team_info is None:
        reply = text(
            "Пожалуйста, введите данные в корректном формате.",
            "/update_team team_name api_host api_key (опционально)",
        )
        await message.reply(reply)
        return

    current_team_info = await db_service.get_team_by_chat(message.chat.id)

    try:
        await db_service.update_team(current_team_info.team_id, updated_team_info)
        reply = (
            "Данные по вашей команде были обновлены. Воспользуйтесь командой /show_current_team."
        )
    except TeamNotFoundError:
        reply = "Команда от вашега чата не найдена. Скорее всего, что вы еще не регистрировались."
    except DuplicatedTeamError as e:
        if e.column == "title":
            reply = text(
                f"Команда с именем `{updated_team_info.title}` уже существует.",
                "Пожалуйста, выберите другое имя команды.",
            )
        elif e.column == "api_base_url":
            reply = text(
                f"Хост: `{updated_team_info.api_base_url}` уже кем-то используется.",
                "Пожалуйста, выберите другой хост.",
            )
        else:
            reply = text(
                "Что-то пошло не так.",
                "Пожалуйста, попробуйте зарегистрироваться через несколько минут.",
            )
    await message.reply(reply)


async def show_current_team_h(message: types.Message, db_service: DBService) -> None:
    try:
        team_info = await db_service.get_team_by_chat(message.chat.id)
        api_key = team_info.api_key if team_info.api_key is not None else "Отсутствует"
        reply = text(
            f"{bold('Команда')}: {team_info.title}",
            f"{bold('Хост')}: {team_info.api_base_url}",
            f"{bold('API Токен')}: {api_key}",
            sep="\n",
        )
    except TeamNotFoundError:
        reply = text(
            "Команда от вашега чата не найдена. Скорее всего, что вы еще не регистрировались."
        )

    await message.reply(reply, parse_mode=ParseMode.MARKDOWN)


async def other_messages_h(message: types.Message, db_service: DBService) -> None:
    await message.reply("Я не поддерживаю Inline команды. Пожалуйста, воспользуйтесь /help.")


def register_handlers(dp: Dispatcher, db_service: DBService, config: ServiceConfig) -> None:
    bot_name = config.telegram_config.bot_name
    command_handlers_mapping = {
        "start": start_h,
        "help": help_h,
        "register_team": register_team_h,
        "update_team": update_team_h,
        "show_current_team": show_current_team_h,
    }

    for command, handler in command_handlers_mapping.items():
        dp.register_message_handler(partial(handle, handler, db_service), commands=[command])

    dp.register_message_handler(
        partial(handle, other_messages_h, db_service), regexp=rf"@{bot_name}"
    )
