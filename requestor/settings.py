import typing as tp
from enum import Enum

from pydantic import BaseSettings, PostgresDsn
from rectools.metrics import MAP
from rectools.metrics.base import MetricAtK


class Env(str, Enum):
    TEST = "TEST"
    PRODUCTION = "PRODUCTION"


class Config(BaseSettings):
    class Config:
        case_sensitive = False


class LogConfig(Config):
    level: str = "INFO"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"

    class Config:
        case_sensitive = False
        fields = {
            "level": {"env": ["log_level"]},
        }


class DBPoolConfig(Config):
    db_url: PostgresDsn
    min_size: int = 0
    max_size: int = 20
    max_queries: int = 1000
    max_inactive_connection_lifetime: int = 3600
    timeout: float = 10
    command_timeout: float = 10
    statement_cache_size: int = 1024
    max_cached_statement_lifetime: int = 3600


class DBConfig(Config):
    db_pool_config: DBPoolConfig
    n_attempts: int = 3
    attempts_interval: int = 2


class TelegramConfig(Config):
    bot_token: str
    bot_name: str
    webhook_host: str
    port: int
    host: str = "0.0.0.0"  # nosec
    webhook_path_pattern: str = "/webhook/{bot_token}"
    team_models_display_limit: int = 10
    metric_by_assessor_display_precision: float = 0.7
    delay_between_messages: int = 4


class GSConfig(Config):
    credentials: str
    url: str
    global_leaderboard_page_name: str
    global_leaderboard_page_max_rows: int

    class Config:
        case_sensitive = False
        env_prefix = "GS_"


class AssessorConfig(Config):
    reco_size: int = 10

    @property
    def main_metric_name(self) -> str:
        return f"MAP@{self.reco_size}"

    @property
    def metrics(self) -> tp.Dict[str, MetricAtK]:
        return {
            f"MAP@{self.reco_size}": MAP(k=self.reco_size),
        }


class GunnerConfig(Config):
    request_url_template: str = "{api_base_url}/reco/{model_name}/{user_id}"
    max_resp_bytes_size: int = 10_000
    max_n_times_requested: int = 3
    user_request_batch_size: int = 1_000

    started_trial_limit: int = 5
    waiting_trial_limit: int = 1
    success_trial_limit: int = 5
    failed_trial_limit: int = 20

    timeout: int = 5
    # it doesn't really belong here, but it's convenient
    progress_update_period: int = 8
    length_to_cut_when_incorrect_content_type: int = 1000


class S3Config(Config):
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region: str
    bucket: str
    key: str
    max_attempts: int = 10

    class Config:
        case_sensitive = False
        env_prefix = "S3_"


class ServiceConfig(Config):
    log_config: LogConfig
    db_config: DBConfig
    telegram_config: TelegramConfig
    gs_config: GSConfig
    assessor_config: AssessorConfig
    gunner_config: GunnerConfig
    s3_config: S3Config

    env: Env = Env.TEST
    run_migrations: bool = False
    migration_attempts: int = 10


def get_config() -> ServiceConfig:
    return ServiceConfig(
        log_config=LogConfig(),
        db_config=DBConfig(db_pool_config=DBPoolConfig()),
        telegram_config=TelegramConfig(),
        gs_config=GSConfig(),
        assessor_config=AssessorConfig(),
        gunner_config=GunnerConfig(),
        s3_config=S3Config(),
    )


# IDE doesn't understand that it ServiceConfig
# if type hint isn't provided
config: ServiceConfig = get_config()


class TrialLimit(int, Enum):
    started = config.gunner_config.started_trial_limit
    waiting = config.gunner_config.waiting_trial_limit
    success = config.gunner_config.success_trial_limit
    failed = config.gunner_config.failed_trial_limit
