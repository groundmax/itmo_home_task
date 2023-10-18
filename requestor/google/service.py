import typing as tp
from tempfile import NamedTemporaryFile

import gspread
from asgiref.sync import sync_to_async
from pydantic import BaseModel  # pylint: disable=no-name-in-module

from requestor.models import ByModelLeaderboardRow, GlobalLeaderboardRow

DT_FMT = "%Y-%m-%d %H:%M:%S"


class GSService(BaseModel):
    credentials: str
    url: str
    global_leaderboard_page_name: str
    global_leaderboard_page_max_rows: int
    by_model_leaderboard_page_name: str
    by_model_leaderboard_page_max_rows: int

    sheet: tp.Optional[gspread.Spreadsheet] = None

    class Config:
        arbitrary_types_allowed = True

    async def setup(self) -> None:
        return await sync_to_async(self._setup)()

    def _setup(self) -> None:
        with NamedTemporaryFile("w+") as f:
            f.write(self.credentials)
            f.seek(0)
            sa = gspread.service_account(f.name)
        self.sheet = sa.open_by_url(self.url)

    def _check_setup(self) -> None:
        if self.sheet is None:
            raise RuntimeError("Setup before using")

    async def update_global_leaderboard(self, rows: tp.List[GlobalLeaderboardRow]) -> None:
        return await sync_to_async(self._update_global_leaderboard)(rows)

    def _update_global_leaderboard(self, rows: tp.List[GlobalLeaderboardRow]) -> None:
        self._check_setup()

        values = [
            [
                i,
                row.team_name,
                row.best_score if row.best_score is not None else "-",
                row.n_attempts,
                row.last_attempt.strftime(DT_FMT) if row.last_attempt is not None else "-",
            ]
            for i, row in enumerate(rows, 1)
        ]

        ws = self.sheet.worksheet(self.global_leaderboard_page_name)
        ws.batch_clear([f"A2:E{self.global_leaderboard_page_max_rows}"])
        ws.update(f"A2:E{len(rows) + 1}", values, raw=False)

    async def update_by_model_leaderboard(self, rows: tp.List[ByModelLeaderboardRow]) -> None:
        return await sync_to_async(self._update_by_model_leaderboard)(rows)

    def _update_by_model_leaderboard(self, rows: tp.List[ByModelLeaderboardRow]) -> None:
        self._check_setup()

        values = [
            [
                row.team_name,
                row.model_name,
                row.best_score,
                row.n_attempts,
                row.last_attempt.strftime(DT_FMT),
            ]
            for row in rows
        ]

        ws = self.sheet.worksheet(self.by_model_leaderboard_page_name)
        ws.batch_clear([f"A2:E{self.by_model_leaderboard_page_max_rows}"])
        ws.update(f"A2:E{len(rows) + 1}", values, raw=False)
