FROM python:3.8-buster as build

COPY . .

RUN pip install -U --no-cache-dir pip poetry setuptools wheel && \
    poetry build -f wheel && \
    poetry export -f requirements.txt -o requirements.txt --without-hashes && \
    pip wheel -w dist -r requirements.txt


FROM python:3.8-slim as runtime

WORKDIR /usr/src/app

# setup timezone
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONOPTIMIZE true
ENV DEBIAN_FRONTEND noninteractive

COPY --from=build dist dist

RUN pip install -U --no-cache-dir pip dist/*.whl && \
    rm -rf dist

COPY --from=build migrations migrations
COPY --from=build alembic.ini main.py ./

CMD ["python", "main.py"]
