import typing as tp

import gspread
from asgiref.sync import sync_to_async
from pydantic import BaseModel

from requestor.models import GlobalLeaderboardRow

DT_FMT = "%Y-%m-%d %H:%M:%S"


class GSService(BaseModel):
    credentials_file_name: str
    url: str
    global_leaderboard_page_name: str
    global_leaderboard_page_max_rows: int

    sheet: tp.Optional[gspread.Spreadsheet] = None

    class Config:
        arbitrary_types_allowed = True

    async def setup(self) -> None:
        return await sync_to_async(self._setup)()

    def _setup(self) -> None:
        sa = gspread.service_account(self.credentials_file_name)
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
