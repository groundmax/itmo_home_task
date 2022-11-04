import datetime
import io
import typing as tp
import uuid
from tempfile import TemporaryFile

import boto3
import pandas as pd

from requestor.settings import StorageServiceConfig

TZ_UTC = datetime.timezone.utc

T = tp.TypeVar("T")


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(TZ_UTC).replace(tzinfo=None)


def make_uuid() -> str:
    return str(uuid.uuid4())


def chunkify(array: tp.List[T], chunk_size: int) -> tp.List[tp.List[T]]:
    if chunk_size <= 0:
        raise ValueError("`chunk_size` should be positive number")

    chunks = []
    for i in range(0, len(array), chunk_size):
        chunks.append(array[i : i + chunk_size])

    return chunks


def download_file_body(service_config: StorageServiceConfig) -> bytes:
    client = boto3.client(
        service_name="s3",
        endpoint_url=service_config.endpoint_url,
        region_name=service_config.region,
        aws_access_key_id=service_config.access_key_id,
        aws_secret_access_key=service_config.secret_access_key,
    )
    with TemporaryFile("w+b") as f:
        client.download_fileobj(service_config.bucket, service_config.key, f)
        f.seek(0)
        body = f.read()
    return body


def get_interactions_from_s3(service_config: StorageServiceConfig) -> pd.DataFrame:
    body = download_file_body(service_config)
    interactions = pd.read_csv(io.BytesIO(body))

    return interactions
