import typing as tp

from aiogram import types
from aiogram.utils.markdown import bold, escape_md, text

from requestor.models import Model, TeamInfo, TrialStatus

from .constants import DATETIME_FORMAT, TrialLimit


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
        return token, TeamInfo(
            title=title, chat_id=message.chat.id, api_base_url=api_base_url, api_key=api_key
        )
    except NameError:
        return None, None


def parse_msg_with_model_info(
    message: types.Message,
) -> tp.Tuple[tp.Optional[str], tp.Optional[str]]:
    args = message.get_args().split(maxsplit=1)
    n_args = len(args)
    if n_args == 2:
        name, description = args
    elif n_args == 1:
        name = args[0]
        description = None

    try:
        return name, description
    except NameError:
        return None, None


def parse_msg_with_request_info(message: types.Message) -> tp.Optional[str]:
    args = message.get_args().split()
    n_args = len(args)

    if n_args == 1:
        return args[0]

    return None


def validate_today_trial_stats(trial_stats: tp.Dict[TrialStatus, int]) -> None:

    if trial_stats[TrialStatus.success] >= TrialLimit.success:
        raise ValueError(
            f"Вы уже совершили {TrialLimit.success} успешных попыток. "
            "Пожалуйста, подождите следующего дня."
        )

    if trial_stats[TrialStatus.waiting] >= TrialLimit.waiting:
        raise ValueError(
            f"Сейчас в очереди на проверку уже есть {TrialLimit.waiting} моделей. "
            "Пожалуйста, подождите пока завершаться проверки этих моделей."
        )

    if trial_stats[TrialStatus.failed] >= TrialLimit.failed:
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
