import asyncio
import datetime
import io
import typing as tp
import uuid
from functools import partial
from tempfile import TemporaryFile

import boto3
import pandas as pd
from botocore.exceptions import EndpointConnectionError

from requestor.log import app_logger
from requestor.settings import S3Config

TZ_UTC = datetime.timezone.utc

T = tp.TypeVar("T")


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(TZ_UTC).replace(tzinfo=None)


def make_uuid() -> str:
    return str(uuid.uuid4())


def do_with_retries(  # type: ignore[return]
    func: tp.Callable[[], T],
    exc_type: tp.Type[Exception],
    max_attempts: int,
) -> T:
    for attempt in range(1, max_attempts + 1):
        app_logger.info(f"Attempt {attempt}")
        try:
            return func()
        except exc_type as e:
            app_logger.info(f"Caught exception on attempt {attempt}: {e!r}")
            if attempt == max_attempts:
                raise


async def async_do_with_retries(  # type: ignore[return]
    func: tp.Awaitable[T],
    exc_type: tp.Union[tp.Type[Exception], tp.Tuple[tp.Type[Exception], ...]],
    max_attempts: int,
    interval: int,
) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            return await func
        except exc_type as e:
            app_logger.error(f"Caught exception on attempt {attempt}: {e!r}")
            if attempt == max_attempts:
                raise
            await asyncio.sleep(interval)


def chunkify(array: tp.List[T], chunk_size: int) -> tp.List[tp.List[T]]:
    if chunk_size <= 0:
        raise ValueError("`chunk_size` should be positive number")

    chunks = []
    for i in range(0, len(array), chunk_size):
        chunks.append(array[i : i + chunk_size])

    return chunks


def download_file_body(s3_config: S3Config) -> bytes:
    app_logger.info("Downloading interactions...")
    client = boto3.client(
        service_name="s3",
        endpoint_url=s3_config.endpoint_url,
        region_name=s3_config.region,
        aws_access_key_id=s3_config.access_key_id,
        aws_secret_access_key=s3_config.secret_access_key,
    )
    with TemporaryFile("w+b") as f:
        func = partial(client.download_fileobj, s3_config.bucket, s3_config.key, f)
        do_with_retries(func, EndpointConnectionError, s3_config.max_attempts)
        f.seek(0)
        body = f.read()
    return body


def get_interactions_from_s3(s3_config: S3Config) -> pd.DataFrame:
    body = download_file_body(s3_config)
    interactions = pd.read_csv(io.BytesIO(body))

    return interactions
