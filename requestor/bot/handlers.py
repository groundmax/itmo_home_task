import asyncio
import traceback
import typing as tp
from datetime import datetime
from functools import partial

from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils.exceptions import RetryAfter
from aiogram.utils.markdown import bold, escape_md, text

from requestor.db import (
    DuplicatedModelError,
    DuplicatedTeamError,
    ModelNotFoundError,
    TeamNotFoundError,
    TokenNotFoundError,
)
from requestor.gunner import (
    DuplicatedRecommendationsError,
    HTTPAuthorizationError,
    HTTPResponseNotOKError,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
    RequestTimeoutError,
)
from requestor.log import app_logger
from requestor.models import ModelInfo, ProgressNotifier, TeamInfo, Trial, TrialStatus
from requestor.services import App
from requestor.settings import ServiceConfig, config
from requestor.utils import utc_now

from .bot_utils import (
    generate_models_description,
    parse_msg_with_model_info,
    parse_msg_with_request_info,
    parse_msg_with_team_info,
    url_validator,
    validate_today_trial_stats,
)
from .commands import BotCommands
from .constants import (
    AVAILABLE_FOR_UPDATE,
    INCORRECT_DATA_IN_MSG,
    MODEL_NOT_FOUND_MSG,
    TEAM_NOT_FOUND_MSG,
)
from .exceptions import InvalidURLError, TooManyRequestsError

DELAY: tp.Final = config.telegram_config.delay_between_messages
PRECISION: tp.Final = config.telegram_config.metric_by_assessor_display_precision

LAST_MSG_TS_BY_CHAT: tp.Dict[int, datetime] = {}


def validate_request_time(message: types.Message) -> None:
    if message.chat.id not in LAST_MSG_TS_BY_CHAT:
        LAST_MSG_TS_BY_CHAT[message.chat.id] = utc_now()
    else:
        previous_request_time = LAST_MSG_TS_BY_CHAT[message.chat.id]
        current_request_time = utc_now()
        LAST_MSG_TS_BY_CHAT[message.chat.id] = current_request_time

        if (current_request_time - previous_request_time).seconds < DELAY:
            raise TooManyRequestsError(
                f"{message.chat.title}({message.chat.id}) requested bot command too early"
            )


def get_message_description(message: types.Message) -> str:
    user = message.from_user["username"]
    msg_id = message.message_id
    msg_text = message.text
    msg_desc = f"[{msg_id} ({msg_text}), from: {user}]"

    chat = message.chat.title
    if chat is not None:
        msg_desc = msg_desc[:-1] + f", chat: {chat}]"

    return msg_desc


async def handle(handler, app: App, message: types.Message) -> None:
    msg_desc = get_message_description(message)

    app_logger.info(f"Got msg {msg_desc}")
    try:
        validate_request_time(message)
        await handler(message, app)

    except TooManyRequestsError as e:
        app_logger.warning(e)
    except RetryAfter as e:
        app_logger.warning(e)
        await asyncio.sleep(e.timeout)
        await handler(message, app)
    except Exception:
        app_logger.error(traceback.format_exc())
        raise
    app_logger.info(f"Msg {msg_desc} handled")


async def start_h(message: types.Message, app: App) -> None:
    reply = text(
        "Привет! Я бот, который будет проверять сервисы",
        "в рамках курса по рекомендательным системам.",
        "Наберите /help для вывода списка доступных команд.",
    )
    await message.reply(reply)


async def help_h(event: types.Message, app: App) -> None:
    reply = BotCommands.get_description_for_available_commands()
    await event.reply(reply)


async def register_team_h(message: types.Message, app: App) -> None:
    try:
        token, team_info = parse_msg_with_team_info(message)
    except InvalidURLError as e:
        return await message.reply(e)

    if team_info is None:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    try:
        await app.db_service.add_team(team_info, token)
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


async def update_team_h(  # noqa: C901 # pylint: disable=too-many-branches
    message: types.Message, app: App
) -> None:
    try:
        current_team_info = await app.db_service.get_team_by_chat(message.chat.id)
    except TeamNotFoundError:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    try:
        update_field, update_value = message.get_args().split()
    except ValueError:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    if update_field not in AVAILABLE_FOR_UPDATE:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    if update_field == "api_base_url":
        try:
            url_validator(update_value)
        except InvalidURLError as e:
            return await message.reply(e)
        if update_value.endswith("/"):
            update_value = update_value[:-1]

    updated_team_info = TeamInfo(**current_team_info.dict())

    setattr(updated_team_info, update_field, update_value)

    try:
        await app.db_service.update_team(current_team_info.team_id, updated_team_info)
        reply = text(
            "Данные по вашей команде успешно обновлены.",
            "Воспользуйтесь командой /show_team",
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


async def show_team_h(message: types.Message, app: App) -> None:
    try:
        team_info = await app.db_service.get_team_by_chat(message.chat.id)
        api_key = team_info.api_key if team_info.api_key is not None else "Отсутствует"
        reply = text(
            f"{bold('Команда')}: {escape_md(team_info.title)}",
            f"{bold('Хост')}: {escape_md(team_info.api_base_url)}",
            f"{bold('API Токен')}: {escape_md(api_key)}",
            sep="\n",
        )
    except TeamNotFoundError:
        reply = escape_md(TEAM_NOT_FOUND_MSG)

    await message.reply(reply, parse_mode=ParseMode.MARKDOWN_V2)


async def add_model_h(message: types.Message, app: App) -> None:
    name, description = parse_msg_with_model_info(message)

    if name is None:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    try:
        team = await app.db_service.get_team_by_chat(message.chat.id)
    except TeamNotFoundError:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    try:
        await app.db_service.add_model(
            ModelInfo(team_id=team.team_id, name=name, description=description)
        )
        reply = f"Модель `{name}` успешно добавлена. Воспользуйтесь командой /show_models"
    except DuplicatedModelError:
        reply = text(
            "Модель с таким именем уже существует.",
            "Пожалуйста, придумайте другое название для модели.",
        )

    await message.reply(reply)


async def show_models_h(message: types.Message, app: App) -> None:
    try:
        team = await app.db_service.get_team_by_chat(message.chat.id)
    except TeamNotFoundError:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    models = await app.db_service.get_team_last_n_models(
        team.team_id, config.telegram_config.team_models_display_limit
    )

    if len(models) == 0:
        reply = "У вашей команды пока еще нет добавленных моделей"
    else:
        reply = generate_models_description(models)

    await message.reply(reply, parse_mode=ParseMode.MARKDOWN_V2)


async def request_h(  # pylint: disable=too-many-branches # noqa: C901
    message: types.Message, app: App
) -> None:
    try:
        team = await app.db_service.get_team_by_chat(message.chat.id)
    except TeamNotFoundError:
        return await message.reply(TEAM_NOT_FOUND_MSG)

    try:
        model_name = parse_msg_with_request_info(message)
    except ValueError:
        return await message.reply(INCORRECT_DATA_IN_MSG)

    try:
        model = await app.db_service.get_model_by_name(team.team_id, model_name)
    except ModelNotFoundError:
        return await message.reply(MODEL_NOT_FOUND_MSG)

    today_trials = await app.db_service.get_team_today_trial_stat(team.team_id)

    try:
        validate_today_trial_stats(today_trials)
    except ValueError as e:
        return await message.reply(e)

    trial: Trial = await app.db_service.add_trial(
        model_id=model.model_id, status=TrialStatus.waiting
    )

    message_to_update = await message.reply(
        "Заявку приняли, начинаем запрашивать рекомендации от сервиса."
    )

    await asyncio.sleep(DELAY)
    notifier = ProgressNotifier(message=message_to_update)

    try:
        raw_recos = await app.gunner_service.get_recos(
            api_base_url=team.api_base_url,
            model_name=model_name,
            notifier=notifier,
            api_token=team.api_key,
        )
        reply, status = "Рекомендации от сервиса успешно получили!", TrialStatus.success
    except (
        HugeResponseSizeError,
        RecommendationsLimitSizeError,
        RequestLimitByUserError,
        DuplicatedRecommendationsError,
        HTTPAuthorizationError,
        HTTPResponseNotOKError,
        RequestTimeoutError,
    ) as e:
        reply, status = e.args[0], TrialStatus.failed
    except Exception:  # pylint: disable=broad-except
        reply, status = "Что-то пошло не по плану, попробуйте позже.", TrialStatus.failed

    await app.db_service.update_trial_status(trial.trial_id, status=status)

    if status != TrialStatus.success:
        return await message.reply(reply)

    await asyncio.sleep(DELAY)
    await notifier.send_progress_update(reply)

    prepared_recos = await app.assessor_service.prepare_recos(raw_recos)
    metrics_data = await app.assessor_service.estimate_recos(prepared_recos)

    for metric in metrics_data:
        if metric.name == config.assessor_config.main_metric_name:
            await asyncio.sleep(DELAY)
            await notifier.send_progress_update(
                f"Результат {metric.name} = {metric.value:{PRECISION}f}"
            )

    await app.db_service.add_metrics(trial_id=trial.trial_id, metrics=metrics_data)

    rows = await app.db_service.get_global_leaderboard(config.assessor_config.main_metric_name)
    await app.gs_service.update_global_leaderboard(rows)
    await asyncio.sleep(DELAY)
    await message.reply("Лидерборд обновлен, можете смотреть результаты.")


async def other_messages_h(message: types.Message, app: App) -> None:
    await message.reply("Я не поддерживаю Inline команды. Пожалуйста, воспользуйтесь /help.")


def register_handlers(dp: Dispatcher, app: App, service_config: ServiceConfig) -> None:
    bot_name = service_config.telegram_config.bot_name
    # TODO: probably automate this dict with getting attributes from globals
    command_handlers_mapping = {
        BotCommands.start.name: start_h,
        BotCommands.help.name: help_h,
        BotCommands.register_team.name: register_team_h,
        BotCommands.update_team.name: update_team_h,
        BotCommands.show_team.name: show_team_h,
        BotCommands.add_model.name: add_model_h,
        BotCommands.show_models.name: show_models_h,
        BotCommands.request.name: request_h,
    }

    for command, handler in command_handlers_mapping.items():
        # TODO: think of way to remove partial
        dp.register_message_handler(partial(handle, handler, app), commands=[command])

    dp.register_message_handler(partial(handle, other_messages_h, app), regexp=rf"@{bot_name}")
