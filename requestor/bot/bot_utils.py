import typing as tp
from urllib.parse import urlsplit

from aiogram import types
from aiogram.utils.markdown import bold, escape_md, text
from pydantic import ValidationError

from requestor.models import Model, TeamInfo, TrialStatus
from requestor.settings import TrialLimit

from .constants import DATETIME_FORMAT
from .exceptions import IncorrectValueError, InvalidURLError


def is_url_valid(url: str) -> bool:
    try:
        scheme, netloc, _, _, _ = urlsplit(url)
        return all([scheme, netloc])
    except Exception:  # pylint: disable=broad-except
        return False


def url_validator(url: str) -> None:
    if not is_url_valid(url):
        raise InvalidURLError("Введенный url некорректен, пожалуйста, проверьте его.")


# TODO: somehow try generalize this func to reduce duplicate code
def parse_msg_with_team_info(
    message: types.Message,
) -> tp.Tuple[tp.Optional[str], tp.Optional[TeamInfo]]:
    args = message.get_args().split()
    n_args = len(args)
    if n_args == 4:
        token, title, api_base_url, api_key = args
    elif n_args == 3:
        token, title, api_base_url = args
        api_key = None

    try:
        url_validator(api_base_url)

        if api_base_url.endswith("/"):
            api_base_url = api_base_url[:-1]

        return token, TeamInfo(
            title=title,
            chat_id=message.chat.id,
            api_base_url=api_base_url,
            api_key=api_key,
        )
    except NameError:
        return None, None
    except ValidationError as e:
        err = e.errors()[0]
        raise IncorrectValueError(f"Недопустимое значение {err['loc'][0]}: {err['msg']}")


def parse_msg_with_model_info(
    message: types.Message,
) -> tp.Tuple[tp.Optional[str], tp.Optional[str]]:
    args = message.get_args().split(maxsplit=1)
    n_args = len(args)
    if n_args == 2:
        name, description = args
    elif n_args == 1:
        name, description = args[0], None

    try:
        return name, description
    except NameError:
        return None, None


def parse_msg_with_request_info(message: types.Message) -> str:
    args = message.get_args().split()
    n_args = len(args)

    if n_args == 1:
        return args[0]

    raise ValueError()


def validate_today_trial_stats(trial_stats: tp.Dict[TrialStatus, int]) -> None:

    if trial_stats.get(TrialStatus.success, 0) >= TrialLimit.success:
        raise ValueError(
            f"Вы уже совершили {TrialLimit.success} успешных попыток. "
            "Пожалуйста, подождите следующего дня."
        )

    if trial_stats.get(TrialStatus.waiting, 0) >= TrialLimit.waiting:
        raise ValueError(
            f"Количество моделей в очереди на проверку: {TrialStatus.waiting}, "
            f"предел: {TrialLimit.waiting}. "
            "Пожалуйста, подождите пока завершатся проверки этих моделей."
        )

    if trial_stats.get(TrialStatus.failed, 0) >= TrialLimit.failed:
        raise ValueError(
            f"Вы уже совершили {TrialLimit.failed} неудачных попыток. "
            "Пожалуйста, подождите следующего дня."
        )


def generate_model_description(model: Model, model_num: int) -> str:
    description = model.description or "Отсутствует"
    created_at = model.created_at.strftime(DATETIME_FORMAT)
    return text(
        bold(model_num),
        f"{bold('Название')}: {escape_md(model.name)}",
        f"{bold('Описание')}: {escape_md(description)}",
        f"{bold('Дата добавления (UTC)')}: {escape_md(created_at)}",
        sep="\n",
    )


def generate_models_description(models: tp.List[Model]) -> str:
    model_descriptions = []
    for model_num, model in enumerate(models, 1):
        model_description = generate_model_description(model, model_num)
        model_descriptions.append(model_description)

    reply = "\n\n".join(model_descriptions)
    return reply
