from datetime import datetime

import gspread
import pytest

from requestor.google import GSService
from requestor.models import GlobalLeaderboardRow
from requestor.settings import ServiceConfig

pytestmark = pytest.mark.asyncio


async def test_global_leaderboard(
    spreadsheet: gspread.Spreadsheet,
    gs_service: GSService,
    service_config: ServiceConfig,
) -> None:
    ws = spreadsheet.worksheet(service_config.gs_config.global_leaderboard_page_name)
    header = ws.row_values(1)

    t1 = datetime(2022, 10, 23, 15, 16, 17)
    t2 = datetime(2022, 9, 7, 1, 2, 3)
    rows = [
        GlobalLeaderboardRow(team_name="team_1", best_score=50, n_attempts=2, last_attempt=t1),
        GlobalLeaderboardRow(team_name="team_2", best_score=30, n_attempts=3, last_attempt=t2),
        GlobalLeaderboardRow(team_name="team_3", best_score=None, n_attempts=0, last_attempt=None),
    ]

    await gs_service.update_global_leaderboard(rows)

    actual_values = ws.get_all_values()

    expected_values = [
        header,
        ["1", "team_1", "50", "2", "2022-10-23 15:16:17"],
        ["2", "team_2", "30", "3", "2022-09-07 1:02:03"],
        ["3", "team_3", "-", "0", "-"],
    ]

    assert actual_values == expected_values
