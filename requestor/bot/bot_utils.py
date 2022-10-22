import typing as tp

from aiogram import types
from aiogram.utils.markdown import bold, escape_md, text
from requestor.models import Model, TeamInfo
from datetime import timedelta
from .constants import DATE_FORMAT

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

def generate_model_description(model: Model, model_num: int) -> str:
    msc_time = model.created_at + timedelta(hours=3)
    description =  "Отсутствует" if model.description is None else model.description
    return text(
        bold(f"Модель #{model_num}"),
        f"{bold('Название')}: {escape_md(model.name)}",
        f"{bold('Описание')}: {escape_md(description)}",
        f"{bold('Дата добавления по МСК')}: {escape_md(msc_time.strftime(DATE_FORMAT))}",
        sep="\n",
    )


def generate_models_description(models: tp.List[Model]) -> tp.List[str]:
    model_descriptions = []
    for model_num, model in enumerate(models, 1):
        model_description = generate_model_description(model, model_num)
        model_descriptions.append(model_description)

    reply = "\n\n".join(model_descriptions)
    return reply
