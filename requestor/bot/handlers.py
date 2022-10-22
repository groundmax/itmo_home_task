import traceback
from functools import partial

from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, escape_md, text
from datetime import timedelta

from requestor.db import (
    DBService,
    DuplicatedModelError,
    DuplicatedTeamError,
    TeamNotFoundError,
    TokenNotFoundError,
)
from requestor.log import app_logger
from requestor.models import ModelInfo, TeamInfo
from requestor.settings import ServiceConfig

from .bot_utils import parse_msg_with_model_info, parse_msg_with_team_info
from .commands import BotCommands
from .constants import AVAILABLE_FOR_UPDATE, INCORRECT_DATA_IN_MSG, TEAM_NOT_FOUND_MSG


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
    reply = BotCommands.get_description_for_available_commands()
    await event.reply(reply)


async def register_team_h(message: types.Message, db_service: DBService) -> None:
    token, team_info = parse_msg_with_team_info(message)

    if team_info is None:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    try:
        await db_service.add_team(team_info, token)
        reply = f"Команда `{team_info.title}` успешно зарегистрирована!"
    except TokenNotFoundError:
        reply = text(
            "Токен не найден. Пожалуйста, проверьте написание.",
            f"Точно ли токен: {token}?",
            sep="\n",
        )
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
    current_team_info = await db_service.get_team_by_chat(message.chat.id)

    # TODO: think of way to generalize this pattern to reduce duplicate code
    if current_team_info is None:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    try:
        update_field, update_value = message.get_args().split()
    except ValueError:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    if update_field not in AVAILABLE_FOR_UPDATE:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    updated_team_info = TeamInfo(**current_team_info.dict())

    setattr(updated_team_info, update_field, update_value)

    try:
        await db_service.update_team(current_team_info.team_id, updated_team_info)
        reply = text(
            "Данные по вашей команде успешно обновлены.",
            "Воспользуйтесь командой /show_team.",
        )
    except DuplicatedTeamError as e:
        if e.column == "api_base_url":
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


async def show_team_h(message: types.Message, db_service: DBService) -> None:
    try:
        team_info = await db_service.get_team_by_chat(message.chat.id)
        api_key = team_info.api_key if team_info.api_key is not None else "Отсутствует"
        reply = text(
            f"{bold('Команда')}: {escape_md(team_info.title)}",
            f"{bold('Хост')}: {escape_md(team_info.api_base_url)}",
            f"{bold('API Токен')}: {escape_md(api_key)}",
            sep="\n",
        )
    except TeamNotFoundError:
        reply = TEAM_NOT_FOUND_MSG

    await message.reply(reply, parse_mode=ParseMode.MARKDOWN_V2)


async def add_model_h(message: types.Message, db_service: DBService) -> None:
    name, description = parse_msg_with_model_info(message)

    if name is None:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    team = await db_service.get_team_by_chat(message.chat.id)

    if team is None:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    try:
        await db_service.add_model(
            ModelInfo(team_id=team.team_id, name=name, description=description)
        )
        reply = f"Модель `{name}` успешно добавлена. Воспользуйтесь командой /show_models"
    except DuplicatedModelError:
        reply = text(
            "Модель с таким именем уже существует.",
            "Пожалуйста, придумайте другое название для модели.",
        )

    await message.reply(reply)


async def show_models_h(message: types.Message, db_service: DBService) -> None:
    team = await db_service.get_team_by_chat(message.chat.id)

    if team is None:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    models = await db_service.get_team_models(team.team_id)

    if len(models) == 0:
        return await message.reply("У вашей команды пока еще нет добавленных моделей")
    else:
        # TODO: get this filters in sql query
        models.sort(key=lambda x: x.created_at, reverse=True)
        models = models[:5]
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        model_descriptions = []
        for model_num, model in enumerate(models, 1):
            msc_time = model.created_at + timedelta(hours=3)
            description =  "Отсутствует" if model.description is None else model.description
            model_description = text(
                bold(f"Модель #{model_num}"),
                f"{bold('Название')}: {escape_md(model.name)}",
                f"{bold('Описание')}: {escape_md(description)}",
                f"{bold('Дата добавления по МСК')}: {escape_md(msc_time.strftime(dt_fmt))}",
                sep="\n",
            )
            model_descriptions.append(model_description)

        reply = "\n\n".join(model_descriptions)

    await message.reply(reply, parse_mode=ParseMode.MARKDOWN_V2)

# TODO: create request handler
async def request_h(message: types.Message, db_service: DBService) -> None:
    raise NotImplementedError


async def other_messages_h(message: types.Message, db_service: DBService) -> None:
    await message.reply("Я не поддерживаю Inline команды. Пожалуйста, воспользуйтесь /help.")


def register_handlers(dp: Dispatcher, db_service: DBService, config: ServiceConfig) -> None:
    bot_name = config.telegram_config.bot_name
    # TODO: probably automate this dict with getting attributes from globals
    command_handlers_mapping = {
        BotCommands.start.name: start_h,
        BotCommands.help.name: help_h,
        BotCommands.register_team.name: register_team_h,
        BotCommands.update_team.name: update_team_h,
        BotCommands.show_team.name: show_team_h,
        BotCommands.add_model.name: add_model_h,
        BotCommands.show_models.name: show_models_h,
    }

    for command, handler in command_handlers_mapping.items():
        # TODO: think of way to remove partial
        dp.register_message_handler(partial(handle, handler, db_service), commands=[command])

    dp.register_message_handler(
        partial(handle, other_messages_h, db_service), regexp=rf"@{bot_name}"
    )
