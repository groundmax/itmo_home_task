from pydantic import BaseSettings, PostgresDsn


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


class GSConfig(Config):
    credentials_file_name: str
    url: str
    global_leaderboard_page_name: str
    global_leaderboard_page_max_rows: int

    class Config:
        case_sensitive = False
        env_prefix = "GS_"


class ServiceConfig(Config):
    log_config: LogConfig
    db_config: DBConfig
    telegram_config: TelegramConfig
    gs_config: GSConfig


def get_config() -> ServiceConfig:
    return ServiceConfig(
        log_config=LogConfig(),
        db_config=DBConfig(db_pool_config=DBPoolConfig()),
        telegram_config=TelegramConfig(),
        gs_config=GSConfig(),
    )
