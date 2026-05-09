import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = os.environ["DB_URL"]
        _engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"options": "-csearch_path=macrohero,public"},
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


@contextmanager
def get_db():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def execute_sql(sql_str: str, params: dict | None = None):
    with get_db() as db:
        result = db.execute(text(sql_str), params or {})
        return result


def fetch_all(sql_str: str, params: dict | None = None) -> list[dict]:
    with get_db() as db:
        result = db.execute(text(sql_str), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


def fetch_one(sql_str: str, params: dict | None = None) -> dict | None:
    with get_db() as db:
        result = db.execute(text(sql_str), params or {})
        row = result.fetchone()
        if row is None:
            return None
        columns = result.keys()
        return dict(zip(columns, row))
