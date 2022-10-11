import re

from asyncpg import UniqueViolationError


class DuplicatedTeamError(Exception):
    def __init__(self, base_error: UniqueViolationError) -> None:
        super().__init__()
        self.column = re.search(r"Key \((\w+)\)=", base_error.detail).group(1)

    def __str__(self) -> str:
        return f"Team with the same value in '{self.column}' column has already exist"


class TeamNotFoundError(Exception):
    pass
