import re

from asyncpg import UniqueViolationError


class DuplicatedError(Exception):
    subject: str = "row"

    def __init__(self, base_error: UniqueViolationError) -> None:
        super().__init__()
        self.column = re.search(r"Key \(([\w, ]+)\)=", base_error.detail).group(1)

    def __str__(self) -> str:
        return f"{self.subject} with the same value in '{self.column}' column already exists"


class DuplicatedTeamError(DuplicatedError):
    subject = "team"


class DuplicatedModelError(DuplicatedError):
    subject = "model"


class DuplicatedMetricError(DuplicatedError):
    subject = "metric"


class NotFoundError(Exception):
    pass


class TeamNotFoundError(NotFoundError):
    pass


class ModelNotFoundError(NotFoundError):
    pass


class TrialNotFoundError(NotFoundError):
    pass
