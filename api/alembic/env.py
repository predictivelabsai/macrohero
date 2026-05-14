import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from macrohero.config import get_settings
from macrohero.db import models  # noqa: F401  ensure all models are registered
from macrohero.db.base import SCHEMA, Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def _include_object(object_, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    """Restrict autogenerate to objects inside SCHEMA. Without this, a shared
    Postgres instance with other apps' schemas would trigger spurious DROPs."""
    if type_ == "schema":
        return name == SCHEMA
    if type_ == "table":
        return getattr(object_, "schema", None) == SCHEMA
    parent_table = getattr(object_, "table", None)
    if parent_table is not None:
        return getattr(parent_table, "schema", None) == SCHEMA
    return True


def _configure(connection: Connection | None = None, **extra: object) -> None:
    """Common configure() options. version_table_schema keeps alembic_version
    inside our schema so dropping it is a clean rollback. include_schemas lets
    autogenerate detect schema-qualified tables; include_object filters them
    down to our schema only."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_object=_include_object,
        **extra,  # type: ignore[arg-type]
    )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    _configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Bootstrap: create our schema if it doesn't exist before any migrations run.
        await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
