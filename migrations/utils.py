from pathlib import Path

from alembic import command as alembic_command
from alembic import config as alembic_config

CURRENT_DIR = Path(__file__).parent
ALEMBIC_INI_PATH = CURRENT_DIR.parent / "alembic.ini"


def upgrade_db() -> None:
    cfg = alembic_config.Config(str(ALEMBIC_INI_PATH))
    alembic_command.upgrade(cfg, "head")
