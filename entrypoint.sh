#!/bin/sh

if [ "${RUN_MIGRATIONS}" = "TRUE" ]; then
    alembic upgrade head
fi

python main.py
