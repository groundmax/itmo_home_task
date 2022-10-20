import os
import secrets
import string
import typing as tp
from contextlib import contextmanager

import click
import psycopg2
from psycopg2.extensions import connection

ALPHABET = string.ascii_uppercase
TOKEN_LENGTH = 16
DB_URL_ENV = "DB_URL"


def generate_token() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(TOKEN_LENGTH))


@contextmanager
def open_pg_connection(db_url: str) -> tp.Generator[connection, None, None]:
    conn = psycopg2.connect(db_url, connect_timeout=1)
    try:
        yield conn
    finally:
        conn.close()


def add_token_to_db(db_url: str, team_description: str, token: str) -> None:
    with open_pg_connection(db_url) as conn:
        with conn.cursor() as cursor:
            sql = "INSERT INTO tokens (token, team_description) VALUES (%s, %s)"
            cursor.execute(sql, (token, team_description))
        conn.commit()


@click.command()
@click.argument("team_description")
def main(team_description: str) -> None:
    """
    Generate token and insert in to DB (given by DB_URL env)
    together with given description
    """
    token = generate_token()
    try:
        db_url = os.environ[DB_URL_ENV]
    except KeyError:
        click.echo(f"`{DB_URL_ENV}` env not set", err=True)
        return

    try:
        add_token_to_db(db_url, team_description, token)
    except Exception as e:  # pylint: disable=broad-except
        click.echo(f"Error while inserting token to DB: {e!r}", err=True)
        return

    click.echo(f"Description: {team_description}  |  Token: {token}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
