import datetime
import typing as tp
import uuid

TZ_UTC = datetime.timezone.utc


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(TZ_UTC).replace(tzinfo=None)


def make_uuid() -> str:
    return str(uuid.uuid4())


def chunkify(array: tp.List[tp.Any], chunk_size: int) -> tp.List[tp.List[tp.Any]]:
    if chunk_size <= 0:
        raise ValueError("`chunk_size` should be positive number")

    chunks = []
    for i in range(0, len(array), chunk_size):
        chunks.append(array[i : i + chunk_size])

    return chunks
