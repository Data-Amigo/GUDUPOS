"""Database setup.

- Laptop: SQLite file (no setup).
- Railway / Vercel: Postgres from DATABASE_URL (on Vercel, use Neon from the Vercel Marketplace).
"""
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

ON_VERCEL = bool(os.getenv("VERCEL"))


def _database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""
    if not url:
        if ON_VERCEL:
            # Vercel functions have no lasting disk: a SQLite file would vanish between requests.
            raise RuntimeError("DATABASE_URL is not set. Add a Postgres database (e.g. Neon) to this Vercel project.")
        url = "sqlite:///./gudu_pos.db"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif ON_VERCEL:
    # Serverless: don't hold connections open between invocations (use Neon's pooled URL).
    engine = create_engine(DATABASE_URL, poolclass=NullPool)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def prepare_database() -> None:
    """Create tables. A local SQLite file from the single-business prototype is rebuilt."""
    insp = inspect(engine)
    if IS_SQLITE and "staff" in insp.get_table_names():
        if "business_id" not in {c["name"] for c in insp.get_columns("staff")}:
            print("Old prototype database found: rebuilding it for multi-business accounts.")
            Base.metadata.drop_all(engine)
            with engine.begin() as conn:
                for t in inspect(engine).get_table_names():
                    conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{t}"')
    Base.metadata.create_all(engine)
