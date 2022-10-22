import typing as tp

from aiogram import types

from requestor.models import TeamInfo


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
