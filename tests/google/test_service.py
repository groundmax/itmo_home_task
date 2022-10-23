from datetime import timedelta

import gspread
import pytest

from requestor.google import GSService
from requestor.google.service import DT_FMT
from requestor.models import GlobalLeaderboardRow
from requestor.settings import ServiceConfig
from requestor.utils import utc_now

pytestmark = pytest.mark.asyncio


async def test_global_leaderboard(
    spreadsheet: gspread.Spreadsheet,
    gs_service: GSService,
    service_config: ServiceConfig,
) -> None:
    ws = spreadsheet.worksheet(service_config.gs_config.global_leaderboard_page_name)
    header = ws.row_values(1)

    t1 = utc_now()
    t2 = t1 - timedelta(hours=2)
    rows = [
        GlobalLeaderboardRow(team_name="team_1", best_score=50, n_attempts=2, last_attempt=t2),
        GlobalLeaderboardRow(team_name="team_2", best_score=30, n_attempts=3, last_attempt=t1),
        GlobalLeaderboardRow(team_name="team_3", best_score=None, n_attempts=0, last_attempt=None),
    ]

    await gs_service.update_global_leaderboard(rows)

    actual_values = ws.get_all_values()

    expected_values = [
        header,
        ["1", "team_1", "50", "2", t2.strftime(DT_FMT)],
        ["2", "team_2", "30", "3", t1.strftime(DT_FMT)],
        ["3", "team_3", "-", "0", "-"],
    ]

    assert actual_values == expected_values
