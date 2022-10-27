import typing as tp
from enum import Enum

AVAILABLE_FOR_UPDATE: tp.Final = {
    "api_base_url",
    "api_key",
}


MODEL_NOT_FOUND_MSG: tp.Final = (
    "Модель не была зарегистрирована. Пожалуйста, воспользуйтесь командой /show_models, "
    "посмотреть список доступных моделей"
)

INCORRECT_DATA_IN_MSG: tp.Final = (
    "Пожалуйста, введите данные в корректном формате. Используйте команду /help для справки."
)

TEAM_NOT_FOUND_MSG: tp.Final = (
    "Команда от вашего чата не найдена. Скорее всего, вы еще не регистрировались."
)

TEAM_MODELS_DISPLAY_LIMIT: tp.Final = 10

DATETIME_FORMAT: tp.Final = "%Y-%m-%d %H:%M:%S"


class TrialLimit(int, Enum):
    waiting = 5
    started = 5
    success = 5
    failed = 20
