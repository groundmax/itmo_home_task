import typing as tp
from enum import Enum

from pydantic import BaseSettings, PostgresDsn
from rectools.metrics import MAP, Precision, Recall

MetricAtK = tp.Union[MAP, Recall, Precision]


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


class TelegramConfig(Config):
    bot_token: str
    bot_name: str
    webhook_host: str
    port: int
    host: str = "0.0.0.0"
    webhook_url_pattern: "{webhook_host}/webhook/{bot_token}"
    team_models_display_limit: int = 10


class GSConfig(Config):
    credentials_file_name: str
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
            f"Recall@{self.reco_size}": Recall(k=self.reco_size),
            f"Precision@{self.reco_size}": Precision(k=self.reco_size),
        }


class GunnerConfig(Config):
    request_url_template: str = "{api_base_url}/{model_name}/{user_id}"
    max_resp_bytes_size: int = 10_000
    max_n_times_requested: int = 3
    user_request_batch_size: int = 10_000

    started_trial_limit: int = 5
    waiting_trial_limit: int = 5
    success_trial_limit: int = 5
    failed_trial_limit: int = 20


class ServiceConfig(Config):
    log_config: LogConfig
    db_config: DBConfig
    telegram_config: TelegramConfig
    gs_config: GSConfig
    assessor_config: AssessorConfig
    gunner_config: GunnerConfig


def get_config() -> ServiceConfig:
    return ServiceConfig(
        log_config=LogConfig(),
        db_config=DBConfig(db_pool_config=DBPoolConfig()),
        telegram_config=TelegramConfig(),
        gs_config=GSConfig(),
        assessor_config=AssessorConfig(),
        gunner_config=GunnerConfig(),
    )


# IDE doesn't understand that it ServiceConfig
# if type hint isn't provided
config: ServiceConfig = get_config()


class TrialLimit(int, Enum):
    started = config.gunner_config.started_trial_limit
    waiting = config.gunner_config.waiting_trial_limit
    success = config.gunner_config.success_trial_limit
    failed = config.gunner_config.failed_trial_limit
