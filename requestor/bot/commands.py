import typing as tp
from dataclasses import dataclass
from enum import Enum

from aiogram.types import BotCommand
from aiogram.utils.markdown import text

from requestor.settings import TrialLimit, config

DELAY: tp.Final = config.telegram_config.delay_between_messages


@dataclass
class CommandDescription:
    command_name: str
    short_description: str
    long_description: tp.Optional[str] = None


commands_description = (
    (
        "start",
        "Начало работы с ботом",
    ),
    (
        "help",
        "Список доступных команд",
    ),
    (
        "register_team",
        "Регистрация команды",
        text(
            "С помощью этой команды можно зарегистрировать свою команду",
            "Принимает на вход аргументы через пробел:",
            "token - токен, который генерируется индивидуально для каждой команды.",
            "title - название команды, без пробелов и кавычек.",
            "api_base_url - хост, по которому будет находиться API команды.",
            "api_key - опционально, токен для запрашивания API.",
            "Пример использования:",
            "/register_team MyToken MyTeamName http://myapi.ru/api/v1 MyApiKey",
            sep="\n",
        ),
    ),
    (
        "update_team",
        "Обновление информации команды",
        text(
            "С помощью этой команды можно обновить хост или токен API.",
            "Для этого используются соответствующие аргументы через пробел.",
            "api_base_url - хост, по которому будет находиться API команды.",
            "api_key - токен для запрашивания API.",
            "Пример использования для обновления хоста:",
            "/update_team api_base_url http://myapi.ru/api/v2",
            sep="\n",
        ),
    ),
    (
        "show_team",
        "Вывод информации по текущей команде",
        "Выводит название команды, хост и API токен",
    ),
    (
        "add_model",
        "Добавление новой модели",
        text(
            "С помощью этой команды можно добавить модель для проверки.",
            "Для этого используются следующие аргументы:",
            "name - название модели, без пробелов и кавычек.",
            "description - опционально, более подробное описание модели",
            "Пример использования для добавления модели:",
            "/add_model lightfm_64",
            (
                "Далее модели будут запрашиваться по адресу: "
                f"{config.gunner_config.request_url_template}"
            ),
            (
                "То есть адрес для запроса выглядит, например, так: "
                "http://myapi.ru/api/v1/lightfm_64/178"
            ),
            "Пример использования для добавления модели с описанием:",
            "/add_model lightfm_64 Добавили фичи по юзерам и айтемам",
            sep="\n",
        ),
    ),
    (
        "show_models",
        "Вывод информации по добавленным моделям",
        text(
            "С помощью этой команды можно вывести следующую информацию:",
            (
                "Название, описание (если присутствует) и дату добавления модели по UTC. "
                "Если было добавлено более "
                f"{config.telegram_config.team_models_display_limit} моделей, "
                "то выведутся последние "
                f"{config.telegram_config.team_models_display_limit} по дате добавления "
                "в обратном хронологическом порядке."
            ),
            sep="\n",
        ),
    ),
    (
        "request",
        "Запрос рекомендаций по зарегистрированной модели",
        text(
            "С помощью этой команды можно запустить опрос вашего сервиса.",
            "Для этого на вход принимается следующий аргумент:",
            (
                "name - название модели, которая была "
                "зарегистрирована с помощью команды /add_model"
            ),
            ("Модель запрашивается по адресу: " f"{config.gunner_config.request_url_template}"),
            "Пример использования команды:",
            "/request lightfm_64",
            (
                "Ограничения на запросы в один день: "
                f"не более {TrialLimit.success} успешных, "
                f"не более {TrialLimit.failed} неудачных, "
                f"не более {TrialLimit.waiting} одновременных."
            ),
            f"Каждый юзер должен иметь ровно {config.assessor_config.reco_size} рекоммендаций.",
            sep="\n",
        ),
    ),
)

cmd2cls_desc = {args[0]: CommandDescription(*args) for args in commands_description}


# it can be initialized via Enum("BotCommands", cmd2cls_desc)
# but IDE doesn't provide you with helper annotations
# and you can not add class methods without "hacks"
# TODO: think of simple way instantiate a frozen class
# with typehinting from IDE
class BotCommands(Enum):
    start: CommandDescription = cmd2cls_desc["start"]
    help: CommandDescription = cmd2cls_desc["help"]
    register_team: CommandDescription = cmd2cls_desc["register_team"]
    update_team: CommandDescription = cmd2cls_desc["update_team"]
    show_team: CommandDescription = cmd2cls_desc["show_team"]
    add_model: CommandDescription = cmd2cls_desc["add_model"]
    show_models: CommandDescription = cmd2cls_desc["show_models"]
    request: CommandDescription = cmd2cls_desc["request"]

    @classmethod
    def get_bot_commands(cls) -> tp.List[BotCommand]:
        return [
            BotCommand(command=command.name, description=command.value.short_description)
            for command in BotCommands
        ]

    @classmethod
    def get_description_for_available_commands(cls) -> str:
        descriptions = []
        for command in BotCommands:
            if command not in (BotCommands.start, BotCommands.help):
                descriptions.append(f"/{command.name}\n{command.value.long_description}")

        descriptions.append(
            f"Важно! У бота есть задержка. Он отвечает на команды 1 раз в {DELAY} секунды."
        )

        return "\n\n".join(descriptions)
