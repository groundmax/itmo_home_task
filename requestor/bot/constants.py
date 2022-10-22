import typing as tp

AVAILABLE_FOR_UPDATE: tp.Final = {
    "api_base_url",
    "api_key",
}

INCORRECT_DATA_IN_MSG: tp.Final = (
    "Пожалуйста, введите данные в корректном формате. Используйте команду /help для справки."
)

TEAM_NOT_FOUND_MSG: tp.Final = (
    "Команда от вашего чата не найдена. Скорее всего, вы еще не регистрировались."
)

TEAM_MODELS_DISPLAY_LIMIT: tp.Final = 10

DATE_FORMAT: tp.Final = "%Y-%m-%d %H:%M:%S"
