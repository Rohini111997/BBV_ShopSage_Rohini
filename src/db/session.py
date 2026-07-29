"""
session.py — SQLAlchemy engine/session for ShopSage's Postgres store (Neon).

pool_pre_ping guards against Neon's autosuspend: a connection that went
stale while the instance was scaled to zero gets silently replaced
instead of raising on the next query.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()
