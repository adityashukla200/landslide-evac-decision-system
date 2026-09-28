"""Database engine and session management."""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

# Ensure SQLite storage directory exists if using SQLite
if not settings.is_postgres:
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    parent_dir = Path(db_path).parent
    if parent_dir and not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if not settings.is_postgres else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_columns() -> None:
    """Ensure SQLite schema has latest columns added in migrations."""
    if not settings.is_postgres:
        import sqlite3
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                # Check alerts columns
                cols = [r[1] for r in c.execute("PRAGMA table_info(alerts)").fetchall()]
                if cols:
                    if "drill_flag" not in cols:
                        c.execute("ALTER TABLE alerts ADD COLUMN drill_flag BOOLEAN DEFAULT 0")
                    if "cap_xml" not in cols:
                        c.execute("ALTER TABLE alerts ADD COLUMN cap_xml TEXT")
                    if "cooldown_until" not in cols:
                        c.execute("ALTER TABLE alerts ADD COLUMN cooldown_until DATETIME")
                    conn.commit()
                conn.close()
            except Exception:
                pass


ensure_sqlite_columns()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
