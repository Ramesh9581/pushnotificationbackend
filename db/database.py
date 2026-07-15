"""
db/database.py
SQLAlchemy engine + session factory connected to Supabase (PostgreSQL).
"""

import socket
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Add it in your Render service → Environment settings."
    )

# Build connect_args that force IPv4 and disable GSS encryption.
# Render's free tier does not have IPv6 outbound connectivity, so
# psycopg2 must resolve the hostname to an IPv4 address only.
_connect_args = {
    "gssencmode": "disable",
    "sslmode": "require",
}

# Monkey-patch socket.getaddrinfo to prefer IPv4 on this process.
# This is the simplest way to force psycopg2 to pick the A record
# instead of the AAAA record when both are returned by DNS.
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _ipv4_only_getaddrinfo

# Create the SQLAlchemy engine.
# pool_pre_ping=True reconnects automatically if the connection drops.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency – yields a DB session and closes it after the request.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Quick connectivity check used at startup."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"[DB] Connection error: {exc}")
        return False
